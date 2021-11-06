export interface UpipeEntitiesD {
    node:                 APINode;
    pipe:                 APIPipe;
    processes:            APIProcess[];
    processors:           APIProcessor[];
    processors_instances: APIProcessorInstance[];
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
    config?:      { [key: string]: any };
    id:           string;
    name:         string;
    processor_id: string;
    settings?:    { [key: string]: any };
    type:         number;
}
