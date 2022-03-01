from .base import UPipeEntity, UPipeEntityType
from .http_api import APIResponse, UPipeMessage
from .messages import UPipeMessage, UPipeMessageType, UPipeEntityType
from .node import APINode, UPipeEntity, ResourceType
from .performance import APINodeUsageMessage, NodePerformanceStats, node_server, QStatus, ProcUtilizationEntry, \
    ProcessPerformanceStats
from .pipe import UPipeEntity, APIPipe, SINK_QUEUE_ID, APIPipeControlMessage, PipeActionType, PipeExecutionStatus
from .processor import APIProcSettings, APIProcessor, ProcessorExecutionStatus
from .mem_queue import APIQueue, APIProcQueues
from .message_parser import APIPipeStatusMessage, parse_pipe_message
from .processor_instance import APIProcessorInstance, APIInstanceActionMessage, ProcessorExecutionStatus, \
    ProcessStatsMessage


def parse_message(msg_json: dict):
    base_msg: UPipeMessage = UPipeMessage.parse_obj(msg_json)
    if base_msg.type == UPipeMessageType.PIPE_CONTROL:
        return APIPipeControlMessage.parse_obj(msg_json)
    if base_msg.type == UPipeMessageType.PIPE_STATUS:
        return APIPipeStatusMessage.parse_obj(msg_json)
    if base_msg.type == UPipeMessageType.INSTANCE_ACTION:
        return APIInstanceActionMessage.parse_obj(msg_json)
    if base_msg.type == UPipeMessageType.PROCESS_STATUS:
        return ProcessStatsMessage.parse_obj(msg_json)

    return UPipeMessage.parse_obj(msg_json)
