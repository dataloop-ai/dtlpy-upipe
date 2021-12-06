/* eslint-disable no-use-before-define */

/* eslint-disable no-multi-spaces */

/* eslint-disable camelcase */

/* eslint-disable @typescript-eslint/no-explicit-any */

/* eslint-disable @typescript-eslint/no-unused-vars */

export enum PipeActionType {
    START = 1,
    RESTART = 2,
    PAUSE = 3,
}

export enum UPipeMessageType {
    Q_STATUS = 1,
    Q_UPDATE = 2,
    PROC_REGISTER = 3,
    PROC_TERMINATE = 4,
    PIPE_REGISTER = 5,
    NODE_INIT = 6,
    PIPE_CONTROL = 7,
    PIPE_STATUS = 8,
    CONFIG_UPDATE = 9,
    REGISTRATION_INFO = 10,
}

export enum UPipeEntityType {
    PROCESSOR = 1,
    PROCESSOR_INSTANCE = 2,
    PROCESS = 3,
    PIPELINE = 4,
    PIPELINE_CONTROLLER = 5,
    SERVER = 6,
    NODE = 7,
    QUEUE = 8,
}

export enum PipeExecutionStatus {
    INIT = 1,
    REGISTERED = 2,
    READY = 3,
    PAUSED = 4,
    RUNNING = 5,
    COMPLETED = 6,
}

export enum ProcessorExecutionStatus {
    INIT = 1,
    READY = 3,
    PAUSED = 4,
    RUNNING = 5,
    COMPLETED = 6,
}

export interface UpipeEntities {
    control_message:      APIPipeControlMessage;
    entity_type:          number;
    node:                 APINode;
    pipe:                 APIPipe;
    processes:            APIProcess[];
    processors:           APIProcessor[];
    processors_instances: APIProcessorInstance[];
    response:             APIResponse;
    status_message:       APIPipeStatusMessage;
}

export interface APIPipeControlMessage {
    action:    number;
    body?:     { [key: string]: any };
    dest:      string;
    pipe_name: string;
    scope:     number;
    sender:    string;
    type:      number;
}

export interface APINode {
    config?:          { [key: string]: any };
    controller:       boolean;
    controller_host?: string;
    controller_port?: number;
    id:               string;
    name:             string;
    settings?:        { [key: string]: any };
    type:             number;
}

export interface APIPipe {
    config?:     { [key: string]: any };
    id:          string;
    name:        string;
    processors?: { [key: string]: APIProcessor };
    queues?:     { [key: string]: APIQueue };
    settings?:   { [key: string]: any };
    type?:       number;
}

export interface APIProcessor {
    config?:      { [key: string]: any };
    entry?:       string;
    function?:    string;
    id:           string;
    interpreter?: string;
    name:         string;
    settings?:    Settings;
    type?:        number;
}

export interface Settings {
    autoscale?:         number;
    host?:              string;
    input_buffer_size?: number;
    priority?:          number;
}

export interface APIQueue {
    config?:   { [key: string]: any };
    from_p:    string;
    host?:     string;
    id:        string;
    name:      string;
    settings?: { [key: string]: any };
    size:      number;
    to_p:      string;
    type?:     number;
}

export interface APIProcess {
    config?:      { [key: string]: any };
    entry?:       string;
    function?:    string;
    id:           string;
    instance_id:  number;
    interpreter?: string;
    name:         string;
    pid?:         number;
    settings?:    Settings;
    type?:        number;
}

export interface APIProcessorInstance {
    config?:   { [key: string]: any };
    id:        string;
    name:      string;
    pid:       string;
    settings?: { [key: string]: any };
    type:      number;
}

export interface APIResponse {
    code?:     string;
    data?:     any;
    messages?: UPipeMessage[];
    success:   boolean;
    text?:     string;
}

export interface UPipeMessage {
    body?:  { [key: string]: any };
    dest:   string;
    scope:  number;
    sender: string;
    type:   number;
}

export interface APIPipeStatusMessage {
    body?:     { [key: string]: any };
    dest:      string;
    pipe_name: string;
    scope:     number;
    sender:    string;
    status:    number;
    type:      number;
}
