from __future__ import annotations
from enum import IntEnum
from typing import List

from pydantic import BaseModel
from pydantic.annotated_types import Dict

from .messages import UPipeMessage
from .processor import APIProcessor

from .mem_queue import APIQueue
from .base import UPipeEntityType, UPipeEntity
from collections import deque


class PipeExecutionStatus(IntEnum):
    INIT = 1
    REGISTERED = 2
    READY = 3
    PAUSED = 4
    RUNNING = 5
    COMPLETED = 6
    PENDING_TERMINATION = 7


class PipeActionType(IntEnum):
    START = 1
    RESTART = 2
    PAUSE = 3
    TERMINATE = 4


class PipeNode(BaseModel):
    processor: APIProcessor
    children: List[PipeNode] = []


class APIPipe(UPipeEntity):
    name: str
    root: APIProcessor
    processors: Dict[str, APIProcessor] = {}
    queues: Dict[str, APIQueue] = {}
    type: UPipeEntityType = UPipeEntityType.PIPELINE

    def _get_processor_children(self, proc: APIProcessor):
        return [self.processors[self.queues[q].from_p] for q in self.queues if self.queues[q].from_p == proc.id]

    def processor_tree(self) -> PipeNode:
        root = PipeNode(processor=self.root)

        def map_tree(node: PipeNode):
            children = self._get_processor_children(node.processor)
            for child in children:
                child_node = PipeNode(processor=child)
                node.children.append(child_node)
                map_tree(child_node)
            return node

        map_tree(root)
        return root

    def drain_list(self):
        q = deque()
        q.append(self.root)
        drain_list = []
        while q:
            next_proc: APIProcessor = q.popleft()
            children = self._get_processor_children(next_proc)
            for child in children:
                if child in drain_list:
                    drain_list.remove(child)
                if child != self.root:
                    drain_list.append(child)
                q.append(child)
        return drain_list


class APIPipeControlMessage(UPipeMessage):
    pipe_name: str
    action: PipeActionType

    @staticmethod
    def from_json(json: dict):
        return APIPipeControlMessage.parse_obj(json)


class APIPipeStatusMessage(UPipeMessage):
    pipe_name: str
    status: PipeExecutionStatus

    @staticmethod
    def from_json(json: dict):
        return APIPipeStatusMessage.parse_obj(json)


class PipelineAlreadyExist(Exception):
    def __init__(self, pipeline_id: str, message=f"Pipeline already exist"):
        self.pipeline_id = pipeline_id
        self.message = message = f"Pipeline {pipeline_id} already exist"
        super().__init__(self.message)
