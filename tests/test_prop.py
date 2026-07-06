from PySide6.QtCore import QObject, Property

class A(QObject):
    @Property(str)
    def foo(self):
        return "bar"

a = A()
print(a.foo)
print(a.property("foo"))
