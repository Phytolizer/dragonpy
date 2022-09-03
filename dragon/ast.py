from pydantic import BaseModel


class Expression(BaseModel):
    value: int


class Statement(BaseModel):
    expression: Expression


class Function(BaseModel):
    name: str
    statement: Statement


class Program(BaseModel):
    function: Function
