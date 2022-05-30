/* eslint-disable camelcase */
/* eslint-disable @typescript-eslint/no-this-alias */
import { APIQueue, PerformanceMetric, QueuePerformanceStats, ThroughputPerformanceMetric } from './defs/UpipeEntities'

const defaultMetricValue = { metric_type: 'generic', unit: 'number', value: 0 } 
class DefaultQueuePerformanceStats implements QueuePerformanceStats {
    allocation_counter: PerformanceMetric = defaultMetricValue
    allocation_index: PerformanceMetric = defaultMetricValue 
    dfps_in: ThroughputPerformanceMetric = defaultMetricValue 
    dfps_out: ThroughputPerformanceMetric = defaultMetricValue 
    exe_counter: PerformanceMetric = defaultMetricValue 
    exe_index: PerformanceMetric = defaultMetricValue 
    free_space: PerformanceMetric = defaultMetricValue 
    pending_counter: PerformanceMetric = defaultMetricValue 
    q_id = '' 
    size: PerformanceMetric = defaultMetricValue
}
export class Queue implements APIQueue {
    qDef: APIQueue
    stats:QueuePerformanceStats|null = null 

    constructor (qDef: APIQueue) {
        this.qDef = qDef
        Object.assign(this, qDef)
        this.stats = new DefaultQueuePerformanceStats()
    }

    updateStats (stats:QueuePerformanceStats) {
        this.stats = stats
    }

    config?: { [key: string]: any } | undefined
    from_p!: string
    host?: string | undefined
    id!: string
    name!: string
    settings?: { [key: string]: any } | undefined
    size!: number
    to_p!: string
    type?: number | undefined
}
