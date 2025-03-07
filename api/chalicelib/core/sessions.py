from chalicelib.utils import pg_client, helper, dev
from chalicelib.core import events, sessions_metas, socket_ios, metadata, events_ios, \
    sessions_mobs, issues, projects, errors, resources, assist

SESSION_PROJECTION_COLS = """s.project_id,
                           s.session_id::text AS session_id,
                           s.user_uuid,
                           s.user_id,
                           s.user_agent,
                           s.user_os,
                           s.user_browser,
                           s.user_device,
                           s.user_device_type,
                           s.user_country,
                           s.start_ts,
                           s.duration,
                           s.events_count,
                           s.pages_count,
                           s.errors_count,
                           s.user_anonymous_id,
                           s.platform,
                           s.issue_score,
                           to_jsonb(s.issue_types) AS issue_types,
                            favorite_sessions.session_id NOTNULL            AS favorite,
                            COALESCE((SELECT TRUE
                             FROM public.user_viewed_sessions AS fs
                             WHERE s.session_id = fs.session_id
                               AND fs.user_id = %(userId)s LIMIT 1), FALSE) AS viewed
                               """


def __group_metadata(session, project_metadata):
    meta = []
    for m in project_metadata.keys():
        if project_metadata[m] is not None and session.get(m) is not None:
            meta.append({project_metadata[m]: session[m]})
        session.pop(m)
    return meta


def get_by_id2_pg(project_id, session_id, user_id, full_data=False, include_fav_viewed=False, group_metadata=False):
    with pg_client.PostgresClient() as cur:
        extra_query = []
        if include_fav_viewed:
            extra_query.append("""COALESCE((SELECT TRUE
                                 FROM public.user_favorite_sessions AS fs
                                 WHERE s.session_id = fs.session_id
                                   AND fs.user_id = %(userId)s), FALSE) AS favorite""")
            extra_query.append("""COALESCE((SELECT TRUE
                                 FROM public.user_viewed_sessions AS fs
                                 WHERE s.session_id = fs.session_id
                                   AND fs.user_id = %(userId)s), FALSE) AS viewed""")
        query = cur.mogrify(
            f"""\
            SELECT
                s.*,
                s.session_id::text AS session_id,
                (SELECT project_key FROM public.projects WHERE project_id = %(project_id)s LIMIT 1) AS project_key
                {"," if len(extra_query) > 0 else ""}{",".join(extra_query)}
                {(",json_build_object(" + ",".join([f"'{m}',p.{m}" for m in metadata._get_column_names()]) + ") AS project_metadata") if group_metadata else ''}
            FROM public.sessions AS s {"INNER JOIN public.projects AS p USING (project_id)" if group_metadata else ""}
            WHERE s.project_id = %(project_id)s
                AND s.session_id = %(session_id)s;""",
            {"project_id": project_id, "session_id": session_id, "userId": user_id}
        )
        # print("===============")
        # print(query)
        cur.execute(query=query)

        data = cur.fetchone()
        if data is not None:
            data = helper.dict_to_camel_case(data)
            if full_data:
                if data["platform"] == 'ios':
                    data['events'] = events_ios.get_by_sessionId(project_id=project_id, session_id=session_id)
                    for e in data['events']:
                        if e["type"].endswith("_IOS"):
                            e["type"] = e["type"][:-len("_IOS")]
                    data['crashes'] = events_ios.get_crashes_by_session_id(session_id=session_id)
                    data['userEvents'] = events_ios.get_customs_by_sessionId(project_id=project_id,
                                                                             session_id=session_id)
                    data['mobsUrl'] = sessions_mobs.get_ios(sessionId=session_id)
                    data["socket"] = socket_ios.start_replay(project_id=project_id, session_id=session_id,
                                                             device=data["userDevice"],
                                                             os_version=data["userOsVersion"],
                                                             mob_url=data["mobsUrl"])
                else:
                    data['events'] = events.get_by_sessionId2_pg(project_id=project_id, session_id=session_id,
                                                                 group_clickrage=True)
                    all_errors = events.get_errors_by_session_id(session_id=session_id)
                    data['stackEvents'] = [e for e in all_errors if e['source'] != "js_exception"]
                    # to keep only the first stack
                    data['errors'] = [errors.format_first_stack_frame(e) for e in all_errors if
                                      e['source'] == "js_exception"][
                                     :500]  # limit the number of errors to reduce the response-body size
                    data['userEvents'] = events.get_customs_by_sessionId2_pg(project_id=project_id,
                                                                             session_id=session_id)
                    data['mobsUrl'] = sessions_mobs.get_web(sessionId=session_id)
                    data['resources'] = resources.get_by_session_id(session_id=session_id)

                data['metadata'] = __group_metadata(project_metadata=data.pop("projectMetadata"), session=data)
                data['issues'] = issues.get_by_session_id(session_id=session_id)
                data['live'] = assist.is_live(project_id=project_id, session_id=session_id,
                                              project_key=data["projectKey"])

            return data
    return None


def sessions_args(args, params):
    if params is not None:
        for key in ['userOs', 'userBrowser', 'userCountry', 'path', 'path_in_order', 'after', 'minDuration',
                    'maxDuration', 'sortSessions', 'eventsCount', 'consoleLogCount', 'startDate', 'endDate',
                    'consoleLog', 'location']:
            args[key] = params.get(key)


new_line = "\n"


def __get_sql_operator(op):
    op = op.lower()
    return "=" if op == "is" or op == "on" else "!=" if op == "isnot" else "ILIKE" if op == "contains" else "NOT ILIKE" if op == "notcontains" else "="


def __is_negation_operator(op):
    return op in ("!=", "NOT ILIKE")


def __reverse_sql_operator(op):
    return "=" if op == "!=" else "!=" if op == "=" else "ILIKE" if op == "NOT ILIKE" else "NOT ILIKE"


def __get_sql_operator_multiple(op):
    op = op.lower()
    return " IN " if op == "is" else " NOT IN "


def __get_sql_operator_boolean(op):
    op = op.lower()
    return True if op == "true" else False


def __get_sql_value_multiple(values):
    if isinstance(values, tuple):
        return values
    return tuple([v for v in values])


@dev.timed
def search2_pg(data, project_id, user_id, favorite_only=False, errors_only=False, error_status="ALL",
               count_only=False, issue=None):
    sessions = []
    generic_args = {"startDate": data['startDate'], "endDate": data['endDate'],
                    "projectId": project_id,
                    "userId": user_id}
    with pg_client.PostgresClient() as cur:
        extra_constraints = [
            cur.mogrify("s.project_id = %(project_id)s", {"project_id": project_id}),
            cur.mogrify("s.duration IS NOT NULL", {})
        ]
        extra_from = ""
        fav_only_join = ""
        if favorite_only and not errors_only:
            fav_only_join = "LEFT JOIN public.user_favorite_sessions AS fs ON fs.session_id = s.session_id"
            extra_constraints.append(cur.mogrify("fs.user_id = %(userId)s", {"userId": user_id}))
        events_query_part = ""
        strict = True

        if len(data.get("events", [])) > 0:
            events_query_from = []
            event_index = 0

            for event in data["events"]:
                # TODO: remove this when message_id is removed
                seq_id = False
                event_type = event["type"].upper()
                if event.get("operator") is None:
                    event["operator"] = "is"
                op = __get_sql_operator(event["operator"])
                is_not = False
                if __is_negation_operator(op) and event_index > 0:
                    is_not = True
                    op = __reverse_sql_operator(op)
                event_from = "%s INNER JOIN public.sessions AS ms USING (session_id)"
                event_where = ["ms.project_id = %(projectId)s", "main.timestamp >= %(startDate)s",
                               "main.timestamp <= %(endDate)s", "ms.start_ts >= %(startDate)s",
                               "ms.start_ts <= %(endDate)s"]
                event_args = {"value": helper.string_to_sql_like_with_op(event['value'], op)}
                if event_type not in list(events.SUPPORTED_TYPES.keys()) \
                        or event.get("value") in [None, "", "*"] \
                        and (event_type != events.event_type.ERROR.ui_type \
                             or event_type != events.event_type.ERROR_IOS.ui_type):
                    continue
                if event_type == events.event_type.CLICK.ui_type:
                    event_from = event_from % f"{events.event_type.CLICK.table} AS main "
                    event_where.append(f"main.{events.event_type.CLICK.column} {op} %(value)s")

                elif event_type == events.event_type.INPUT.ui_type:
                    event_from = event_from % f"{events.event_type.INPUT.table} AS main "
                    event_where.append(f"main.{events.event_type.INPUT.column} {op} %(value)s")
                    if len(event.get("custom", "")) > 0:
                        event_where.append("main.value ILIKE %(custom)s")
                        event_args["custom"] = helper.string_to_sql_like_with_op(event['custom'], "ILIKE")
                elif event_type == events.event_type.LOCATION.ui_type:
                    event_from = event_from % f"{events.event_type.LOCATION.table} AS main "
                    event_where.append(f"main.{events.event_type.LOCATION.column} {op} %(value)s")
                elif event_type == events.event_type.CUSTOM.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.CUSTOM.table} AS main "
                    event_where.append(f"main.{events.event_type.CUSTOM.column} {op} %(value)s")
                elif event_type == events.event_type.REQUEST.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.REQUEST.table} AS main "
                    event_where.append(f"main.{events.event_type.REQUEST.column} {op} %(value)s")
                elif event_type == events.event_type.GRAPHQL.ui_type:
                    event_from = event_from % f"{events.event_type.GRAPHQL.table} AS main "
                    event_where.append(f"main.{events.event_type.GRAPHQL.column} {op} %(value)s")
                elif event_type == events.event_type.STATEACTION.ui_type:
                    event_from = event_from % f"{events.event_type.STATEACTION.table} AS main "
                    event_where.append(f"main.{events.event_type.STATEACTION.column} {op} %(value)s")
                elif event_type == events.event_type.ERROR.ui_type:
                    if event.get("source") in [None, "*", ""]:
                        event["source"] = "js_exception"
                    event_from = event_from % f"{events.event_type.ERROR.table} AS main INNER JOIN public.errors AS main1 USING(error_id)"
                    if event.get("value") not in [None, "*", ""]:
                        event_where.append(f"(main1.message {op} %(value)s OR main1.name {op} %(value)s)")
                        if event.get("source") not in [None, "*", ""]:
                            event_where.append(f"main1.source = %(source)s")
                            event_args["source"] = event["source"]
                    elif event.get("source") not in [None, "*", ""]:
                        event_where.append(f"main1.source = %(source)s")
                        event_args["source"] = event["source"]

                # ----- IOS
                elif event_type == events.event_type.CLICK_IOS.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.CLICK_IOS.table} AS main "
                    event_where.append(f"main.{events.event_type.CLICK_IOS.column} {op} %(value)s")

                elif event_type == events.event_type.INPUT_IOS.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.INPUT_IOS.table} AS main "
                    event_where.append(f"main.{events.event_type.INPUT_IOS.column} {op} %(value)s")

                    if len(event.get("custom", "")) > 0:
                        event_where.append("main.value ILIKE %(custom)s")
                        event_args["custom"] = helper.string_to_sql_like_with_op(event['custom'], "ILIKE")
                elif event_type == events.event_type.VIEW_IOS.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.VIEW_IOS.table} AS main "
                    event_where.append(f"main.{events.event_type.VIEW_IOS.column} {op} %(value)s")
                elif event_type == events.event_type.CUSTOM_IOS.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.CUSTOM_IOS.table} AS main "
                    event_where.append(f"main.{events.event_type.CUSTOM_IOS.column} {op} %(value)s")
                elif event_type == events.event_type.REQUEST_IOS.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.REQUEST_IOS.table} AS main "
                    event_where.append(f"main.{events.event_type.REQUEST_IOS.column} {op} %(value)s")
                elif event_type == events.event_type.ERROR_IOS.ui_type:
                    seq_id = True
                    event_from = event_from % f"{events.event_type.ERROR_IOS.table} AS main INNER JOIN public.crashes_ios AS main1 USING(crash_id)"
                    if event.get("value") not in [None, "*", ""]:
                        event_where.append(f"(main1.reason {op} %(value)s OR main1.name {op} %(value)s)")

                else:
                    continue

                event_index += 1
                if is_not:
                    event_from += f""" LEFT JOIN (SELECT session_id FROM {event_from} WHERE {" AND ".join(event_where)}) AS left_not USING (session_id)"""
                    event_where[-1] = "left_not.session_id ISNULL"
                events_query_from.append(cur.mogrify(f"""\
                (SELECT
                    main.session_id, {'seq_index' if seq_id else 'message_id %%%% 2147483647 AS seq_index'}, timestamp, {event_index} AS funnel_step
                  FROM {event_from}
                  WHERE {" AND ".join(event_where)}
                )\
                """, {**generic_args, **event_args}).decode('UTF-8'))

            if len(events_query_from) > 0:
                events_query_part = f"""\
                    SELECT
                        session_id, MIN(timestamp) AS first_event_ts, MAX(timestamp) AS last_event_ts
                    FROM
                    ({(" UNION ALL ").join(events_query_from)}) AS f_query
                    GROUP BY 1
                    {"" if event_index < 2 else f"HAVING events.funnel(array_agg(funnel_step ORDER BY timestamp,seq_index ASC), {event_index})" if strict
                else f"HAVING array_length(array_agg(DISTINCT funnel_step), 1) = {len(data['events'])}"}
                {fav_only_join}
                """
        else:
            data["events"] = []

        # ---------------------------------------------------------------------------
        if "filters" in data:
            meta_keys = metadata.get(project_id=project_id)
            meta_keys = {m["key"]: m["index"] for m in meta_keys}
            for f in data["filters"]:
                if not isinstance(f.get("value"), list):
                    f["value"] = [f.get("value")]
                if len(f["value"]) == 0 or f["value"][0] is None:
                    continue
                filter_type = f["type"].upper()
                f["value"] = __get_sql_value_multiple(f["value"])
                if filter_type == sessions_metas.meta_type.USERBROWSER:
                    op = __get_sql_operator_multiple(f["operator"])
                    extra_constraints.append(
                        cur.mogrify(f's.user_browser {op} %(value)s', {"value": f["value"]}))

                elif filter_type in [sessions_metas.meta_type.USEROS, sessions_metas.meta_type.USEROS_IOS]:
                    op = __get_sql_operator_multiple(f["operator"])
                    extra_constraints.append(cur.mogrify(f's.user_os {op} %(value)s', {"value": f["value"]}))

                elif filter_type in [sessions_metas.meta_type.USERDEVICE, sessions_metas.meta_type.USERDEVICE_IOS]:
                    op = __get_sql_operator_multiple(f["operator"])
                    extra_constraints.append(cur.mogrify(f's.user_device {op} %(value)s', {"value": f["value"]}))

                elif filter_type in [sessions_metas.meta_type.USERCOUNTRY, sessions_metas.meta_type.USERCOUNTRY_IOS]:
                    op = __get_sql_operator_multiple(f["operator"])
                    extra_constraints.append(cur.mogrify(f's.user_country {op} %(value)s', {"value": f["value"]}))
                elif filter_type == "duration".upper():
                    if len(f["value"]) > 0 and f["value"][0] is not None:
                        extra_constraints.append(
                            cur.mogrify("s.duration >= %(minDuration)s", {"minDuration": f["value"][0]}))
                    if len(f["value"]) > 1 and f["value"][1] is not None and f["value"][1] > 0:
                        extra_constraints.append(
                            cur.mogrify("s.duration <= %(maxDuration)s", {"maxDuration": f["value"][1]}))
                elif filter_type == sessions_metas.meta_type.REFERRER:
                    # events_query_part = events_query_part + f"INNER JOIN events.pages AS p USING(session_id)"
                    extra_from += f"INNER JOIN {events.event_type.LOCATION.table} AS p USING(session_id)"
                    op = __get_sql_operator_multiple(f["operator"])
                    extra_constraints.append(
                        cur.mogrify(f"p.base_referrer {op} %(referrer)s", {"referrer": f["value"]}))
                elif filter_type == events.event_type.METADATA.ui_type:
                    op = __get_sql_operator(f["operator"])
                    if f.get("key") in meta_keys.keys():
                        extra_constraints.append(
                            cur.mogrify(f"s.{metadata.index_to_colname(meta_keys[f['key']])} {op} %(value)s",
                                        {"value": helper.string_to_sql_like_with_op(f["value"][0], op)})
                        )
                elif filter_type in [sessions_metas.meta_type.USERID, sessions_metas.meta_type.USERID_IOS]:
                    op = __get_sql_operator(f["operator"])
                    extra_constraints.append(
                        cur.mogrify(f"s.user_id {op} %(value)s",
                                    {"value": helper.string_to_sql_like_with_op(f["value"][0], op)})
                    )
                elif filter_type in [sessions_metas.meta_type.USERANONYMOUSID,
                                     sessions_metas.meta_type.USERANONYMOUSID_IOS]:
                    op = __get_sql_operator(f["operator"])
                    extra_constraints.append(
                        cur.mogrify(f"s.user_anonymous_id {op} %(value)s",
                                    {"value": helper.string_to_sql_like_with_op(f["value"][0], op)})
                    )
                elif filter_type in [sessions_metas.meta_type.REVID, sessions_metas.meta_type.REVID_IOS]:
                    op = __get_sql_operator(f["operator"])
                    extra_constraints.append(
                        cur.mogrify(f"s.rev_id {op} %(value)s",
                                    {"value": helper.string_to_sql_like_with_op(f["value"][0], op)})
                    )

        # ---------------------------------------------------------------------------

        if data.get("startDate") is not None:
            extra_constraints.append(cur.mogrify("s.start_ts >= %(startDate)s", {"startDate": data['startDate']}))
        else:
            data['startDate'] = None
        if data.get("endDate") is not None:
            extra_constraints.append(cur.mogrify("s.start_ts <= %(endDate)s", {"endDate": data['endDate']}))
        else:
            data['endDate'] = None

        if data.get('platform') is not None:
            if data['platform'] == 'mobile':
                extra_constraints.append(b"s.user_os in ('Android','BlackBerry OS','iOS','Tizen','Windows Phone')")
            elif data['platform'] == 'desktop':
                extra_constraints.append(
                    b"s.user_os in ('Chrome OS','Fedora','Firefox OS','Linux','Mac OS X','Ubuntu','Windows')")

        order = "DESC"
        if data.get("order") is not None:
            order = data["order"]
        sort = 'session_id'
        if data.get("sort") is not None and data["sort"] != "session_id":
            sort += " " + order + "," + helper.key_to_snake_case(data["sort"])
        else:
            sort = 'session_id'

        if errors_only:
            extra_from += f" INNER JOIN {events.event_type.ERROR.table} AS er USING (session_id) INNER JOIN public.errors AS ser USING (error_id)"
            extra_constraints.append(b"ser.source = 'js_exception'")
            if error_status != "ALL":
                extra_constraints.append(cur.mogrify("ser.status = %(status)s", {"status": error_status.lower()}))
            if favorite_only:
                extra_from += " INNER JOIN public.user_favorite_errors AS ufe USING (error_id)"
                extra_constraints.append(cur.mogrify("ufe.user_id = %(user_id)s", {"user_id": user_id}))

        extra_constraints = [extra.decode('UTF-8') + "\n" for extra in extra_constraints]
        if not favorite_only and not errors_only:
            extra_from += """LEFT JOIN (SELECT user_id, session_id
                                                                FROM public.user_favorite_sessions
                                                                WHERE user_id = %(userId)s) AS favorite_sessions
                                                               USING (session_id)"""
        extra_join = ""
        if issue is not None:
            extra_join = cur.mogrify("""
            INNER JOIN LATERAL(SELECT TRUE FROM events_common.issues INNER JOIN public.issues AS p_issues USING (issue_id)
            WHERE issues.session_id=f.session_id 
                AND p_issues.type=%(type)s 
                AND p_issues.context_string=%(contextString)s
                AND timestamp >= f.first_event_ts
                AND timestamp <= f.last_event_ts) AS issues ON(TRUE)
            """, {"contextString": issue["contextString"], "type": issue["type"]}).decode('UTF-8')

        query_part = f"""\
                    FROM {f"({events_query_part}) AS f" if len(events_query_part) > 0 else "public.sessions AS s"}
                    {extra_join}
                    {"INNER JOIN public.sessions AS s USING(session_id)" if len(events_query_part) > 0 else ""}
                    {extra_from}
                    WHERE 

                      {" AND ".join(extra_constraints)}"""

        if errors_only:
            main_query = cur.mogrify(f"""\
                                SELECT DISTINCT er.error_id, ser.status, ser.parent_error_id, ser.payload,
                                        COALESCE((SELECT TRUE
                                         FROM public.user_favorite_sessions AS fs
                                         WHERE s.session_id = fs.session_id
                                           AND fs.user_id = %(userId)s), FALSE)   AS favorite,
                                        COALESCE((SELECT TRUE
                                                     FROM public.user_viewed_errors AS ve
                                                     WHERE er.error_id = ve.error_id
                                                       AND ve.user_id = %(userId)s LIMIT 1), FALSE) AS viewed
                                {query_part};""",
                                     generic_args)

        elif count_only:
            main_query = cur.mogrify(f"""\
                                        SELECT COUNT(DISTINCT s.session_id) AS count_sessions, COUNT(DISTINCT s.user_uuid) AS count_users
                                        {query_part};""",
                                     generic_args)
        else:
            main_query = cur.mogrify(f"""\
                                        SELECT * FROM
                                        (SELECT DISTINCT ON(s.session_id) {SESSION_PROJECTION_COLS}
                                        {query_part}
                                        ORDER BY s.session_id desc) AS filtred_sessions
                                        ORDER BY favorite DESC, issue_score DESC, {sort} {order};""",
                                     generic_args)

        # print("--------------------")
        # print(main_query)

        cur.execute(main_query)

        if count_only:
            return helper.dict_to_camel_case(cur.fetchone())
        sessions = []
        total = cur.rowcount
        row = cur.fetchone()
        limit = 200
        while row is not None and len(sessions) < limit:
            if row.get("favorite"):
                limit += 1
            sessions.append(row)
            row = cur.fetchone()

    if errors_only:
        return sessions
    if data.get("sort") is not None and data["sort"] != "session_id":
        sessions = sorted(sessions, key=lambda s: s[helper.key_to_snake_case(data["sort"])],
                          reverse=data.get("order", "DESC").upper() == "DESC")
    return {
        'total': total,
        'sessions': helper.list_to_camel_case(sessions)
    }


def search_by_metadata(tenant_id, user_id, m_key, m_value, project_id=None):
    if project_id is None:
        all_projects = projects.get_projects(tenant_id=tenant_id, recording_state=False)
    else:
        all_projects = [
            projects.get_project(tenant_id=tenant_id, project_id=int(project_id), include_last_session=False,
                                 include_gdpr=False)]

    all_projects = {int(p["projectId"]): p["name"] for p in all_projects}
    project_ids = list(all_projects.keys())

    available_keys = metadata.get_keys_by_projects(project_ids)
    for i in available_keys:
        available_keys[i]["user_id"] = sessions_metas.meta_type.USERID
        available_keys[i]["user_anonymous_id"] = sessions_metas.meta_type.USERANONYMOUSID
    results = {}
    for i in project_ids:
        if m_key not in available_keys[i].values():
            available_keys.pop(i)
            results[i] = {"total": 0, "sessions": [], "missingMetadata": True}
    project_ids = list(available_keys.keys())
    if len(project_ids) > 0:
        with pg_client.PostgresClient() as cur:
            sub_queries = []
            for i in project_ids:
                col_name = list(available_keys[i].keys())[list(available_keys[i].values()).index(m_key)]
                sub_queries.append(cur.mogrify(
                    f"(SELECT COALESCE(COUNT(s.*)) AS count FROM public.sessions AS s WHERE s.project_id = %(id)s AND s.{col_name} = %(value)s) AS \"{i}\"",
                    {"id": i, "value": m_value}).decode('UTF-8'))
            query = f"""SELECT {", ".join(sub_queries)};"""
            cur.execute(query=query)

            rows = cur.fetchone()

            sub_queries = []
            for i in rows.keys():
                results[i] = {"total": rows[i], "sessions": [], "missingMetadata": False, "name": all_projects[int(i)]}
                if rows[i] > 0:
                    col_name = list(available_keys[int(i)].keys())[list(available_keys[int(i)].values()).index(m_key)]
                    sub_queries.append(
                        cur.mogrify(
                            f"""(
                                    SELECT *
                                    FROM (
                                            SELECT DISTINCT ON(favorite_sessions.session_id, s.session_id) {SESSION_PROJECTION_COLS}
                                            FROM public.sessions AS s LEFT JOIN (SELECT session_id
                                                                                    FROM public.user_favorite_sessions
                                                                                    WHERE user_favorite_sessions.user_id = %(userId)s
                                                                                ) AS favorite_sessions USING (session_id)
                                            WHERE s.project_id = %(id)s AND s.duration IS NOT NULL AND s.{col_name} = %(value)s
                                        ) AS full_sessions
                                    ORDER BY favorite DESC, issue_score DESC
                                    LIMIT 10
                                )""",
                            {"id": i, "value": m_value, "userId": user_id}).decode('UTF-8'))
            if len(sub_queries) > 0:
                cur.execute("\nUNION\n".join(sub_queries))
                rows = cur.fetchall()
                for i in rows:
                    results[str(i["project_id"])]["sessions"].append(helper.dict_to_camel_case(i))
    return results


def search_by_issue(user_id, issue, project_id, start_date, end_date):
    constraints = ["s.project_id = %(projectId)s",
                   "p_issues.context_string = %(issueContextString)s",
                   "p_issues.type = %(issueType)s"]
    if start_date is not None:
        constraints.append("start_ts >= %(startDate)s")
    if end_date is not None:
        constraints.append("start_ts <= %(endDate)s")
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT DISTINCT ON(favorite_sessions.session_id, s.session_id) {SESSION_PROJECTION_COLS}
            FROM public.sessions AS s
                                INNER JOIN events_common.issues USING (session_id)
                                INNER JOIN public.issues AS p_issues USING (issue_id)
                                LEFT JOIN (SELECT user_id, session_id
                                            FROM public.user_favorite_sessions
                                            WHERE user_id = %(userId)s) AS favorite_sessions
                                           USING (session_id)
            WHERE {" AND ".join(constraints)}
            ORDER BY s.session_id DESC;""",
                {
                    "issueContextString": issue["contextString"],
                    "issueType": issue["type"], "userId": user_id,
                    "projectId": project_id,
                    "startDate": start_date,
                    "endDate": end_date
                }))

        rows = cur.fetchall()
    return helper.list_to_camel_case(rows)


def get_favorite_sessions(project_id, user_id, include_viewed=False):
    with pg_client.PostgresClient() as cur:
        query_part = cur.mogrify(f"""\
            FROM public.sessions AS s 
                LEFT JOIN public.user_favorite_sessions AS fs ON fs.session_id = s.session_id
            WHERE fs.user_id = %(userId)s""",
                                 {"projectId": project_id, "userId": user_id}
                                 )

        extra_query = b""
        if include_viewed:
            extra_query = cur.mogrify(""",\
            COALESCE((SELECT TRUE
             FROM public.user_viewed_sessions AS fs
             WHERE s.session_id = fs.session_id
               AND fs.user_id = %(userId)s), FALSE) AS viewed""",
                                      {"projectId": project_id, "userId": user_id})

        cur.execute(f"""\
                    SELECT s.project_id,
                           s.session_id::text AS session_id,
                           s.user_uuid,
                           s.user_id,
                           s.user_agent,
                           s.user_os,
                           s.user_browser,
                           s.user_device,
                           s.user_country,
                           s.start_ts,
                           s.duration,
                           s.events_count,
                           s.pages_count,
                           s.errors_count,
                           TRUE AS favorite
                           {extra_query.decode('UTF-8')}                            
                    {query_part.decode('UTF-8')}
                    ORDER BY s.session_id         
                    LIMIT 50;""")

        sessions = cur.fetchall()
    return helper.list_to_camel_case(sessions)


def get_user_sessions(project_id, user_id, start_date, end_date):
    with pg_client.PostgresClient() as cur:
        constraints = ["s.project_id = %(projectId)s", "s.user_id = %(userId)s"]
        if start_date is not None:
            constraints.append("s.start_ts >= %(startDate)s")
        if end_date is not None:
            constraints.append("s.start_ts <= %(endDate)s")

        query_part = f"""\
            FROM public.sessions AS s
            WHERE {" AND ".join(constraints)}"""

        cur.execute(cur.mogrify(f"""\
                    SELECT s.project_id,
                           s.session_id::text AS session_id,
                           s.user_uuid,
                           s.user_id,
                           s.user_agent,
                           s.user_os,
                           s.user_browser,
                           s.user_device,
                           s.user_country,
                           s.start_ts,
                           s.duration,
                           s.events_count,
                           s.pages_count,
                           s.errors_count
                    {query_part}
                    ORDER BY s.session_id         
                    LIMIT 50;""", {
            "projectId": project_id,
            "userId": user_id,
            "startDate": start_date,
            "endDate": end_date
        }))

        sessions = cur.fetchall()
    return helper.list_to_camel_case(sessions)


def get_session_user(project_id, user_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
            SELECT
                user_id,
                count(*) as session_count,	
                max(start_ts) as last_seen,
                min(start_ts) as first_seen
            FROM
                "public".sessions
            WHERE
                project_id = %(project_id)s
                AND user_id = %(user_id)s
                AND duration is not null
            GROUP BY user_id;
            """,
            {"project_id": project_id, "user_id": user_id}
        )
        cur.execute(query=query)
        data = cur.fetchone()
    return helper.dict_to_camel_case(data)


def get_session_ids_by_user_ids(project_id, user_ids):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
            SELECT session_id FROM public.sessions
            WHERE
                project_id = %(project_id)s AND user_id IN %(user_id)s;""",
            {"project_id": project_id, "user_id": tuple(user_ids)}
        )
        ids = cur.execute(query=query)
    return ids


def delete_sessions_by_session_ids(session_ids):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
            DELETE FROM public.sessions
            WHERE
                session_id IN %(session_ids)s;""",
            {"session_ids": tuple(session_ids)}
        )
        cur.execute(query=query)

    return True


def delete_sessions_by_user_ids(project_id, user_ids):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
            DELETE FROM public.sessions
            WHERE
                project_id = %(project_id)s AND user_id IN %(user_id)s;""",
            {"project_id": project_id, "user_id": tuple(user_ids)}
        )
        cur.execute(query=query)

    return True
