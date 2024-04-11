from typing import TypeVar, Generic
import heapq

T = TypeVar('T')
class Heap(Generic[T]):
    def __init__(self) -> None:
        self.data: list[T] = list()
    
    def push(self, value: T):
        heapq.heappush(self.data, value)
    
    def pop(self) -> T:
        return heapq.heappop(self.data)
    
    def peek(self) -> T | None:
        try:
            return self.data[0]
        except IndexError:
            return None
    
    def __bool__(self):
        return len(self.data) > 0
    
    def __len__(self):
        return len(self.data)

    def clear(self):
        self.data.clear()