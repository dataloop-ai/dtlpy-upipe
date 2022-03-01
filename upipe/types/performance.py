from typing import List

from pydantic import BaseModel
from pydantic.class_validators import Optional

from . import UPipeEntity, UPipeMessage

node_server = None


class MetricType:
    COMPUTE = 'compute'
    MEMORY = 'memory'
    DISK_IO = 'disk_io'
    NETWORK_IO = 'network_io'
    THROUGHPUT = 'throughput'
    STORAGE = 'storage'
    GENERIC = 'generic'


class PerformanceMetricUnitType:
    Number = 'number'
    Percentage = 'percentage'
    DFPS = 'dfps'


class PerformanceMetric(BaseModel):
    metric_type: str = 'generic'
    value: float = 0
    unit: str = 'number'

    class Config:
        arbitrary_types_allowed = True


class PercentPerformanceMetric(PerformanceMetric):
    metric_type: str
    unit: str = PerformanceMetricUnitType.Percentage


class ThroughputPerformanceMetric(PerformanceMetric):
    metric_type: str = 'throughput'
    unit: str = PerformanceMetricUnitType.DFPS


class MemoryPerformanceMetric(PercentPerformanceMetric):
    metric_type: str = MetricType.MEMORY
    id: str


class DiskPerformanceMetric(PercentPerformanceMetric):
    metric_type: str = MetricType.STORAGE
    id: str


class CPUPerformanceMetric(PerformanceMetric):
    metric_type: Optional[str] = MetricType.COMPUTE
    value: float
    unit: Optional[str] = PerformanceMetricUnitType.Percentage
    core_id: str


class QueuePerformanceStats(BaseModel):
    dfps_in: ThroughputPerformanceMetric
    dfps_out: ThroughputPerformanceMetric
    allocation_counter: PerformanceMetric
    exe_counter: PerformanceMetric
    pending_counter: PerformanceMetric
    allocation_index: PerformanceMetric
    exe_index: PerformanceMetric
    free_space: PerformanceMetric
    size: PerformanceMetric
    q_id: str


class ProcessPerformanceStats(BaseModel):
    dfps_in: ThroughputPerformanceMetric
    dfps_out: ThroughputPerformanceMetric
    received_counter: PerformanceMetric
    processed_counter: PerformanceMetric
    pid: int


class ProcessorPerformanceStats(BaseModel):
    dfps_in: ThroughputPerformanceMetric
    dfps_out: ThroughputPerformanceMetric
    received_counter: PerformanceMetric
    processed_counter: PerformanceMetric
    pid: int


class ProcessorPerformanceStats(BaseModel):
    instances_stats: List[ProcessPerformanceStats] = []
    processor_id: str
    pipe_id: Optional[str]


class NodePerformanceStats(BaseModel):
    cpu_total: CPUPerformanceMetric
    cores_usage: List[CPUPerformanceMetric] = []
    disks_usage: List[DiskPerformanceMetric] = []
    queues_usage: List[QueuePerformanceStats] = []
    processors_usage: List[ProcessorPerformanceStats] = []
    memory: MemoryPerformanceMetric
    node_id: str


class APINodeUsageMessage(UPipeMessage):
    stats: NodePerformanceStats

    @staticmethod
    def from_json(json: dict):
        return APINodeUsageMessage.parse_obj(json)


class HWUsageMetric(BaseModel):
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    gpu_memory_usage: float
    network_io_usage: float
    disk_io_usage: float


class ProcUtilizationEntry(BaseModel):
    cpu: float
    memory: float
    pending: Optional[int]
    time: int
    proc: UPipeEntity


class QStatus(BaseModel):
    q_id: str
    pending: int
    time: int
