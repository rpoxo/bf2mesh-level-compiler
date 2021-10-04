class Vec3(object):
    def __init__(self, x, y, z):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z
    
    def __str__(self):
        return f'{self.x}, {self.y}, {self.z}'
    
    def __repr__(self):
        return [self.x, self.y, self.z]
    
    def __iter__(self):
        for value in [self.x, self.y, self.z]:
            yield value
    
    def __add__(self, v):
        if isinstance(self, Vec3):
            return Vec3(self.x + v.x, self.y + v.y, self.z + v.z)
        else:
            return Vec3(self.x + v, self.y + v, self.z + v)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __sub__(self, v):
        return self + (-v)

    def __mul__(self, v):
        if isinstance(v, Vec3):
            return Vec3(self.x * v.x, self.y * v.y, self.z * v.z)
        else:
            return Vec3(self.x * v, self.y * v, self.z * v)

    def __rmul__(self, v):
        return self.__mul__(v)

    def __truediv__(self, v):
        if isinstance(v, Vec3):
            return Vec3(self.x / v.x, self.y / v.y, self.z / v.z)
        else:
            return Vec3(self.x / v, self.y / v, self.z / v)