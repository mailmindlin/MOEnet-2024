from typing import TypeVar, Generic, Callable, Type, cast
import abc

T = TypeVar('T')
Tcov = TypeVar('Tcov', covariant=True)
R = TypeVar('R')
class Tracked(Generic[Tcov], abc.ABC):
    @property
    @abc.abstractmethod
    def current(self) -> Tcov:
        "Current tracked value"
        ...

    is_static = False

    @property
    @abc.abstractmethod
    def is_fresh(self) -> bool:
        "Check if the tracked value is still fresh (it hasn't changed)"
        return False

    def refresh(self) -> 'Tracked[Tcov]':
        assert self.is_fresh
        return self

    def map(self, func: Callable[[Tcov], R]) -> 'Tracked[R]':
        if self.is_static and self.is_fresh:
            return StaticValue(func(self.current))
        return Derived(func, self)

class PushValue(Tracked[T]):
    def __init__(self, value: T):
        super().__init__()
        self._value = value
        self.value_next = value
    
    @property
    def current(self):
        return self._value
    
    def update(self, value_next: T):
        self.value_next = value_next
    
    @property
    def is_fresh(self):
        return self.current == self.value_next

    def refresh(self) -> Tracked[T]:
        self._value = self.value_next
        return self

class StaticValue(Tracked[T]):
    def __init__(self, value: T) -> None:
        super().__init__()
        self._value = value
    
    @property
    def current(self):
        return self._value
    
    is_static = True

    @property
    def is_fresh(self):
        return True
    
    def refresh(self):
        return self
    
    def map(self, func: Callable[[T], R]) -> Tracked[R]:
        return StaticValue(func(self.current))
    
    def __hash__(self) -> int:
        return hash(self.current)
    
    def __repr__(self) -> str:
        return f'StaticValue({self.current!r})'
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, StaticValue):
            return __value.current == self.current
        elif isinstance(__value, Tracked):
            return (
                __value.is_static
                and __value.is_fresh
                and __value.current == self.current
            )
        else:
            return False

class undefined(): pass

class Derived(Tracked[T]):
    def __init__(self, func: Callable[..., T], *args: Tracked):
        super().__init__()
        self._func = func
        self._args = args
        self._last_args = None
        self._last_value: Type[undefined] | T = undefined
    
    @property
    def is_static(self):
        return all(arg.is_static for arg in self._args)
    
    @property
    def is_fresh(self):
        if not all(arg.is_fresh for arg in self._args):
            return False
        if self._last_args is not None:
            for arg, last_arg in zip(self._args, self._last_args):
                if arg.current != last_arg:
                    return False
        return True
    
    @property
    def current(self) -> T:
        v = self._last_value
        if v is undefined:
            self._last_args = [arg.current for arg in self._args]
            try:
                self._last_value = self._func(*self._last_args)
                return self._last_value
            except:
                print("Error computing", repr(self))
                raise
        else:
            return cast(T, v)
    
    def refresh(self) -> Tracked[T]:
        replace = False
        args_static = True
        res_args: list[Tracked] = list()
        for arg in self._args:
            arg1 = arg.refresh()
            args_static &= arg1.is_static and arg1.is_fresh
            replace |= (arg1 is not arg)
            res_args.append(arg1)
        
        if replace:
            # Rebuild if args changed
            res = Derived(self._func, *res_args)
        else:
            res = self
            res._last_args = None
            res._last_value = undefined
        
        if args_static:
            # Simplify
            return StaticValue(res.current)
        return res

    def __repr__(self) -> str:
        return f'Derived(func={self._func}, args={repr(self._args)})'