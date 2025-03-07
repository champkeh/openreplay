import { Loader, NoContent, DropdownPlain } from 'UI';
import { widgetHOC, Styles, AvgLabel } from '../common';
import { withRequest } from 'HOCs';
import { ResponsiveContainer, AreaChart, XAxis, YAxis, CartesianGrid, Area, Tooltip } from 'recharts';
import WidgetAutoComplete from 'Shared/WidgetAutoComplete';
import { LAST_24_HOURS, LAST_30_MINUTES, YESTERDAY, LAST_7_DAYS } from 'Types/app/period';

const WIDGET_KEY = 'resourcesLoadingTime';
const toUnderscore = s => s.split(/(?=[A-Z])/).join('_').toLowerCase();

// other' = -1, 'script' = 0, 'stylesheet' = 1, 'fetch' = 2, 'img' = 3, 'media' = 4
export const RESOURCE_OPTIONS = [
  { text: 'All', value: 'all', },
  { text: 'JS', value: "SCRIPT", },
  { text: 'CSS', value: "STYLESHEET", },
  { text: 'Fetch', value: "REQUEST", },
  { text: 'Image', value: "IMG", },
  { text: 'Media', value: "MEDIA", },
  { text: 'Other', value: "OTHER", },
];

const customParams = rangeName => {
  const params = {density: 70, type: null }

  if (rangeName === LAST_24_HOURS) params.density = 70
  if (rangeName === LAST_30_MINUTES) params.density = 70
  if (rangeName === YESTERDAY) params.density = 70
  if (rangeName === LAST_7_DAYS) params.density = 70
  
  return params
}

@withRequest({
	dataName: "options",
  initialData: [],
  dataWrapper: data => data,  
  loadingName: 'optionsLoading',
	requestName: "fetchOptions",
	endpoint: '/dashboard/' + toUnderscore(WIDGET_KEY) + '/search',
	method: 'GET'
})
@widgetHOC(WIDGET_KEY, { customParams })
export default class ResourceLoadingTime extends React.PureComponent {
  state = { autoCompleteSelected: null, type: null }
  onSelect = (params) => {
    const _params = customParams(this.props.period.rangeName)
    this.setState({ autoCompleteSelected: params.value });
    this.props.fetchWidget(WIDGET_KEY, this.props.period, this.props.platform, { ..._params, url: params.value })
  }

  writeOption = (e, { name, value }) => {
    this.setState({ [name]: value })
    const _params = customParams(this.props.period.rangeName)
    this.props.fetchWidget(WIDGET_KEY, this.props.period, this.props.platform, { ..._params, [ name ]: value === 'all' ? null : value  })
  }

  render() {
    const { data, loading, period, optionsLoading, compare = false, showSync = false } = this.props;
    const { autoCompleteSelected, type } = this.state;
    const colors = compare ? Styles.compareColors : Styles.colors;
    const params = customParams(period.rangeName)
    const gradientDef = Styles.gradientDef();

    return (
      <NoContent
        size="small"
        show={ data.chart.length === 0 }
      >
        <React.Fragment>
          <div className="flex items-center mb-3">
            <WidgetAutoComplete
              loading={optionsLoading}
              fetchOptions={this.props.fetchOptions}
              options={this.props.options}
              onSelect={this.onSelect}
              placeholder="Search for Fetch, CSS or Media"
              filterParams={{ type: type }}
            />
            <DropdownPlain
              disabled={!!autoCompleteSelected}
              name="type"
              label="Resource"
              options={ RESOURCE_OPTIONS }
              onChange={ this.writeOption }
              defaultValue={'all'}
              wrapperStyle={{
                position: 'absolute',
                top: '12px',
                left: '170px',
              }}
            />
            <AvgLabel className="ml-auto" text="Avg" count={Math.round(data.avg)} unit="ms" />
          </div>
          <Loader loading={ loading } size="small">
            <NoContent
              size="small"
              show={ data.chart.size === 0 }
            >
              <ResponsiveContainer height={ 200 } width="100%">
                <AreaChart
                  data={ data.chart }
                  margin={ Styles.chartMargins }
                  syncId={ showSync ? WIDGET_KEY : undefined }
                >
                  {gradientDef}
                  <CartesianGrid strokeDasharray="3 3" vertical={ false } stroke="#EEEEEE" />
                  <XAxis {...Styles.xaxis} dataKey="time" interval={params.density/7} />
                  <YAxis
                    {...Styles.yaxis}
                    tickFormatter={val => Styles.tickFormatter(val)}
                    label={{ ...Styles.axisLabelLeft, value: "Resource Fetch Time (ms)" }}
                  />
                  <Tooltip {...Styles.tooltip} />
                  <Area
                    name="Avg"
                    unit=" ms"
                    type="monotone"
                    dataKey="avg"
                    stroke={colors[0]}
                    fillOpacity={ 1 }
                    strokeWidth={ 2 }
                    strokeOpacity={ 0.8 }
                    fill={compare ? 'url(#colorCountCompare)' : 'url(#colorCount)'}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </NoContent>
          </Loader>
        </React.Fragment>
      </NoContent>
    );
  }
}
