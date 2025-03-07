// Auto-generated, do not edit

import PrimitiveReader from './PrimitiveReader';

export const ID_TP_MAP = {

  0: "timestamp",
  4: "set_page_location",
  5: "set_viewport_size",
  6: "set_viewport_scroll",
  7: "create_document",
  8: "create_element_node",
  9: "create_text_node",
  10: "move_node",
  11: "remove_node",
  12: "set_node_attribute",
  13: "remove_node_attribute",
  14: "set_node_data",
  15: "set_css_data",
  16: "set_node_scroll",
  18: "set_input_value",
  19: "set_input_checked",
  20: "mouse_move",
  22: "console_log",
  37: "css_insert_rule",
  38: "css_delete_rule",
  39: "fetch_depricated",
  40: "profiler",
  41: "o_table",
  44: "redux",
  45: "vuex",
  46: "mob_x",
  47: "ng_rx",
  48: "graph_ql",
  49: "performance_track",
  54: "connection_information",
  55: "set_page_visibility",
  59: "long_task",
  68: "fetch",
} as const;


export interface Timestamp {
  tp: "timestamp",
  timestamp: number,
}

export interface SetPageLocation {
  tp: "set_page_location",
  url: string,
  referrer: string,
  navigationStart: number,
}

export interface SetViewportSize {
  tp: "set_viewport_size",
  width: number,
  height: number,
}

export interface SetViewportScroll {
  tp: "set_viewport_scroll",
  x: number,
  y: number,
}

export interface CreateDocument {
  tp: "create_document",

}

export interface CreateElementNode {
  tp: "create_element_node",
  id: number,
  parentID: number,
  index: number,
  tag: string,
  svg: boolean,
}

export interface CreateTextNode {
  tp: "create_text_node",
  id: number,
  parentID: number,
  index: number,
}

export interface MoveNode {
  tp: "move_node",
  id: number,
  parentID: number,
  index: number,
}

export interface RemoveNode {
  tp: "remove_node",
  id: number,
}

export interface SetNodeAttribute {
  tp: "set_node_attribute",
  id: number,
  name: string,
  value: string,
}

export interface RemoveNodeAttribute {
  tp: "remove_node_attribute",
  id: number,
  name: string,
}

export interface SetNodeData {
  tp: "set_node_data",
  id: number,
  data: string,
}

export interface SetCssData {
  tp: "set_css_data",
  id: number,
  data: string,
}

export interface SetNodeScroll {
  tp: "set_node_scroll",
  id: number,
  x: number,
  y: number,
}

export interface SetInputValue {
  tp: "set_input_value",
  id: number,
  value: string,
  mask: number,
}

export interface SetInputChecked {
  tp: "set_input_checked",
  id: number,
  checked: boolean,
}

export interface MouseMove {
  tp: "mouse_move",
  x: number,
  y: number,
}

export interface ConsoleLog {
  tp: "console_log",
  level: string,
  value: string,
}

export interface CssInsertRule {
  tp: "css_insert_rule",
  id: number,
  rule: string,
  index: number,
}

export interface CssDeleteRule {
  tp: "css_delete_rule",
  id: number,
  index: number,
}

export interface FetchDepricated {
  tp: "fetch_depricated",
  method: string,
  url: string,
  request: string,
  response: string,
  status: number,
  timestamp: number,
  duration: number,
}

export interface Profiler {
  tp: "profiler",
  name: string,
  duration: number,
  args: string,
  result: string,
}

export interface OTable {
  tp: "o_table",
  key: string,
  value: string,
}

export interface Redux {
  tp: "redux",
  action: string,
  state: string,
  duration: number,
}

export interface Vuex {
  tp: "vuex",
  mutation: string,
  state: string,
}

export interface MobX {
  tp: "mob_x",
  type: string,
  payload: string,
}

export interface NgRx {
  tp: "ng_rx",
  action: string,
  state: string,
  duration: number,
}

export interface GraphQl {
  tp: "graph_ql",
  operationKind: string,
  operationName: string,
  variables: string,
  response: string,
}

export interface PerformanceTrack {
  tp: "performance_track",
  frames: number,
  ticks: number,
  totalJSHeapSize: number,
  usedJSHeapSize: number,
}

export interface ConnectionInformation {
  tp: "connection_information",
  downlink: number,
  type: string,
}

export interface SetPageVisibility {
  tp: "set_page_visibility",
  hidden: boolean,
}

export interface LongTask {
  tp: "long_task",
  timestamp: number,
  duration: number,
  context: number,
  containerType: number,
  containerSrc: string,
  containerId: string,
  containerName: string,
}

export interface Fetch {
  tp: "fetch",
  method: string,
  url: string,
  request: string,
  response: string,
  status: number,
  timestamp: number,
  duration: number,
  headers: string,
}


export type Message = Timestamp | SetPageLocation | SetViewportSize | SetViewportScroll | CreateDocument | CreateElementNode | CreateTextNode | MoveNode | RemoveNode | SetNodeAttribute | RemoveNodeAttribute | SetNodeData | SetCssData | SetNodeScroll | SetInputValue | SetInputChecked | MouseMove | ConsoleLog | CssInsertRule | CssDeleteRule | FetchDepricated | Profiler | OTable | Redux | Vuex | MobX | NgRx | GraphQl | PerformanceTrack | ConnectionInformation | SetPageVisibility | LongTask | Fetch;

export default function (r: PrimitiveReader): Message | null {
  switch (r.readUint()) {
  
  case 0:
    return {
      tp: ID_TP_MAP[0], 
      timestamp: r.readUint(),      
    };
  
  case 4:
    return {
      tp: ID_TP_MAP[4], 
      url: r.readString(),
      referrer: r.readString(),
      navigationStart: r.readUint(),      
    };
  
  case 5:
    return {
      tp: ID_TP_MAP[5], 
      width: r.readUint(),
      height: r.readUint(),      
    };
  
  case 6:
    return {
      tp: ID_TP_MAP[6], 
      x: r.readInt(),
      y: r.readInt(),      
    };
  
  case 7:
    return {
      tp: ID_TP_MAP[7], 
      
    };
  
  case 8:
    return {
      tp: ID_TP_MAP[8], 
      id: r.readUint(),
      parentID: r.readUint(),
      index: r.readUint(),
      tag: r.readString(),
      svg: r.readBoolean(),      
    };
  
  case 9:
    return {
      tp: ID_TP_MAP[9], 
      id: r.readUint(),
      parentID: r.readUint(),
      index: r.readUint(),      
    };
  
  case 10:
    return {
      tp: ID_TP_MAP[10], 
      id: r.readUint(),
      parentID: r.readUint(),
      index: r.readUint(),      
    };
  
  case 11:
    return {
      tp: ID_TP_MAP[11], 
      id: r.readUint(),      
    };
  
  case 12:
    return {
      tp: ID_TP_MAP[12], 
      id: r.readUint(),
      name: r.readString(),
      value: r.readString(),      
    };
  
  case 13:
    return {
      tp: ID_TP_MAP[13], 
      id: r.readUint(),
      name: r.readString(),      
    };
  
  case 14:
    return {
      tp: ID_TP_MAP[14], 
      id: r.readUint(),
      data: r.readString(),      
    };
  
  case 15:
    return {
      tp: ID_TP_MAP[15], 
      id: r.readUint(),
      data: r.readString(),      
    };
  
  case 16:
    return {
      tp: ID_TP_MAP[16], 
      id: r.readUint(),
      x: r.readInt(),
      y: r.readInt(),      
    };
  
  case 18:
    return {
      tp: ID_TP_MAP[18], 
      id: r.readUint(),
      value: r.readString(),
      mask: r.readInt(),      
    };
  
  case 19:
    return {
      tp: ID_TP_MAP[19], 
      id: r.readUint(),
      checked: r.readBoolean(),      
    };
  
  case 20:
    return {
      tp: ID_TP_MAP[20], 
      x: r.readUint(),
      y: r.readUint(),      
    };
  
  case 22:
    return {
      tp: ID_TP_MAP[22], 
      level: r.readString(),
      value: r.readString(),      
    };
  
  case 37:
    return {
      tp: ID_TP_MAP[37], 
      id: r.readUint(),
      rule: r.readString(),
      index: r.readUint(),      
    };
  
  case 38:
    return {
      tp: ID_TP_MAP[38], 
      id: r.readUint(),
      index: r.readUint(),      
    };
  
  case 39:
    return {
      tp: ID_TP_MAP[39], 
      method: r.readString(),
      url: r.readString(),
      request: r.readString(),
      response: r.readString(),
      status: r.readUint(),
      timestamp: r.readUint(),
      duration: r.readUint(),      
    };
  
  case 40:
    return {
      tp: ID_TP_MAP[40], 
      name: r.readString(),
      duration: r.readUint(),
      args: r.readString(),
      result: r.readString(),      
    };
  
  case 41:
    return {
      tp: ID_TP_MAP[41], 
      key: r.readString(),
      value: r.readString(),      
    };
  
  case 44:
    return {
      tp: ID_TP_MAP[44], 
      action: r.readString(),
      state: r.readString(),
      duration: r.readUint(),      
    };
  
  case 45:
    return {
      tp: ID_TP_MAP[45], 
      mutation: r.readString(),
      state: r.readString(),      
    };
  
  case 46:
    return {
      tp: ID_TP_MAP[46], 
      type: r.readString(),
      payload: r.readString(),      
    };
  
  case 47:
    return {
      tp: ID_TP_MAP[47], 
      action: r.readString(),
      state: r.readString(),
      duration: r.readUint(),      
    };
  
  case 48:
    return {
      tp: ID_TP_MAP[48], 
      operationKind: r.readString(),
      operationName: r.readString(),
      variables: r.readString(),
      response: r.readString(),      
    };
  
  case 49:
    return {
      tp: ID_TP_MAP[49], 
      frames: r.readInt(),
      ticks: r.readInt(),
      totalJSHeapSize: r.readUint(),
      usedJSHeapSize: r.readUint(),      
    };
  
  case 54:
    return {
      tp: ID_TP_MAP[54], 
      downlink: r.readUint(),
      type: r.readString(),      
    };
  
  case 55:
    return {
      tp: ID_TP_MAP[55], 
      hidden: r.readBoolean(),      
    };
  
  case 59:
    return {
      tp: ID_TP_MAP[59], 
      timestamp: r.readUint(),
      duration: r.readUint(),
      context: r.readUint(),
      containerType: r.readUint(),
      containerSrc: r.readString(),
      containerId: r.readString(),
      containerName: r.readString(),      
    };
  
  case 68:
    return {
      tp: ID_TP_MAP[68], 
      method: r.readString(),
      url: r.readString(),
      request: r.readString(),
      response: r.readString(),
      status: r.readUint(),
      timestamp: r.readUint(),
      duration: r.readUint(),
      headers: r.readString(),      
    };
  
  default:
    r.readUint(); // IOS skip timestamp  
    r.skip(r.readUint()); 
    return null;
  }
}
