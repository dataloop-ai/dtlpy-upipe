/* *********** Linter rules *************** */

/* eslint-disable no-use-before-define */

/* eslint-disable no-multi-spaces */

/* eslint-disable camelcase */

/* eslint-disable @typescript-eslint/no-explicit-any */

/* eslint-disable @typescript-eslint/no-unused-vars */

/* *********** Interfaces *************** */

export interface UpipeEntities {
    control_message:      APIPipeControlMessage;
    entity_type:          number;
    node:                 APINode;
    node_stats:           NodePerformanceStats;
    node_stats_message:   APINodeUsageMessage;
    pipe:                 APIPipe;
    processes:            APIProcess[];
    processors:           APIProcessor[];
    processors_instances: APIProcessorInstance[];
    queue_stats:          QueuePerformanceStats;
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
    resources?:       APINodeResource[];
    settings?:        { [key: string]: any };
    type:             number;
}

export interface APINodeResource {
    config?:   { [key: string]: any };
    id:        string;
    name:      string;
    settings?: { [key: string]: any };
    size?:     number;
    type:      string;
}

export interface NodePerformanceStats {
    cores_usage?:      CPUPerformanceMetric[];
    cpu_total:         CPUPerformanceMetric;
    disks_usage?:      DiskPerformanceMetric[];
    memory:            MemoryPerformanceMetric;
    node_id:           string;
    processors_usage?: ProcessorPerformanceStats[];
    queues_usage?:     QueuePerformanceStats[];
}

export interface CPUPerformanceMetric {
    core_id:      string;
    metric_type?: string;
    unit?:        string;
    value:        number;
}

export interface DiskPerformanceMetric {
    id:           string;
    metric_type?: string;
    unit?:        string;
    value?:       number;
}

export interface MemoryPerformanceMetric {
    id:           string;
    metric_type?: string;
    unit?:        string;
    value?:       number;
}

export interface ProcessorPerformanceStats {
    instances_stats?: ProcessPerformanceStats[];
    pipe_id?:         string;
    processor_id:     string;
}

export interface ProcessPerformanceStats {
    dfps_in:           ThroughputPerformanceMetric;
    dfps_out:          ThroughputPerformanceMetric;
    pid:               number;
    processed_counter: PerformanceMetric;
    received_counter:  PerformanceMetric;
}

export interface ThroughputPerformanceMetric {
    metric_type?: string;
    unit?:        string;
    value?:       number;
}

export interface PerformanceMetric {
    metric_type?: string;
    unit?:        string;
    value?:       number;
}

export interface QueuePerformanceStats {
    allocation_counter: PerformanceMetric;
    allocation_index:   PerformanceMetric;
    dfps_in:            ThroughputPerformanceMetric;
    dfps_out:           ThroughputPerformanceMetric;
    exe_counter:        PerformanceMetric;
    exe_index:          PerformanceMetric;
    free_space:         PerformanceMetric;
    pending_counter:    PerformanceMetric;
    q_id:               string;
    size:               PerformanceMetric;
}

export interface APINodeUsageMessage {
    body?:  { [key: string]: any };
    dest:   string;
    scope:  number;
    sender: string;
    stats:  NodePerformanceStats;
    type:   number;
}

export interface APIPipe {
    config?:     { [key: string]: any };
    id:          string;
    name:        string;
    processors?: { [key: string]: APIProcessor };
    queues?:     { [key: string]: APIQueue };
    root:        APIProcessor;
    settings?:   { [key: string]: any };
    sink:        APIQueue;
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
/* *********** Int Enums *************** */
export enum ProcessorExecutionStatus {
    INIT = 1,
    READY = 3,
    PAUSED = 4,
    RUNNING = 5,
    COMPLETED = 6,
    PENDING_TERMINATION = 7,
}
export enum PipeExecutionStatus {
    INIT = 1,
    REGISTERED = 2,
    READY = 3,
    PAUSED = 4,
    RUNNING = 5,
    COMPLETED = 6,
    PENDING_TERMINATION = 7,
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
export enum UPipeMessageType {
    Q_STATUS = 1,
    Q_UPDATE = 2,
    PROC_REGISTER = 3,
    REQUEST_TERMINATION = 4,
    PIPE_REGISTER = 5,
    NODE_INIT = 6,
    PIPE_CONTROL = 7,
    PIPE_STATUS = 8,
    CONFIG_UPDATE = 9,
    REGISTRATION_INFO = 10,
    INSTANCE_ACTION = 11,
    NODE_STATUS = 12,
    PROCESS_STATUS = 13,
}
export enum PipeActionType {
    START = 1,
    RESTART = 2,
    PAUSE = 3,
    TERMINATE = 4,
}
/* *********** Str enums *************** */
export enum ResourceType {
    NODE = 'node',
    CPU = 'cpu',
    GPU = 'gpu',
    TPU = 'tpu',
    MEMORY = 'memory',
    NETWORK_IO = 'network_io',
    DISK_IO = 'disk_io',
    STANDARD_STORAGE = 'standard_storage',
    SSD_STORAGE = 'ssd_storage',
}
export enum MetricType {
    COMPUTE = 'compute',
    MEMORY = 'memory',
    DISK_IO = 'disk_io',
    NETWORK_IO = 'network_io',
    THROUGHPUT = 'throughput',
    STORAGE = 'storage',
    GENERIC = 'generic',
}
export enum PerformanceMetricUnitType {
    Number = 'number',
    Percentage = 'percentage',
    DFPS = 'dfps',
}
