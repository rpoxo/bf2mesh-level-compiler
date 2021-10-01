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
        return [x, y, z]
    
    def __iter__(self):
        for value in [self.x, self.y, self.z]:
            yield value
    
    def __add__(self, v):
        return Vec3(self.x + v.x, self.y + v.y, self.z + v.z)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __sub__(self, v):
        return self + (-v)