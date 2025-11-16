#!/usr/bin/env python3
import unittest
from ebyst.stapl.data import Int, Bool, Any, IntArray, BoolArray, Variable, ArrayVariable
from ebyst.stapl import errors

class TestCalc(unittest.TestCase):
    def test_bool(self):
        self.assertTrue(Bool(True))
        self.assertFalse(Bool(False))

        self.assertTrue(Bool(True) == Bool(True))
        self.assertFalse(Bool(True) == Bool(False))
        self.assertFalse(Bool(False) == Bool(True))
        self.assertTrue(Bool(False) == Bool(False))
        self.assertIsInstance(Bool(True) == Bool(True), Bool)

        self.assertFalse(Bool(True) != Bool(True))
        self.assertTrue(Bool(True) != Bool(False))
        self.assertTrue(Bool(False) != Bool(True))
        self.assertFalse(Bool(False) != Bool(False))
        self.assertIsInstance(Bool(True) != Bool(True), Bool)

        self.assertTrue(Bool(True) and Bool(True))
        self.assertFalse(Bool(True) and Bool(False))
        self.assertFalse(Bool(False) and Bool(True))
        self.assertFalse(Bool(False) and Bool(False))
        self.assertIsInstance(Bool(True) and Bool(True), Bool)

        self.assertTrue(Bool(True) or Bool(True))
        self.assertTrue(Bool(True) or Bool(False))
        self.assertTrue(Bool(False) or Bool(True))
        self.assertFalse(Bool(False) or Bool(False))
        self.assertIsInstance(Bool(True) or Bool(True), Bool)

        self.assertFalse(not Bool(True))
        self.assertTrue(not Bool(False))
        self.assertFalse(~Bool(True))
        self.assertTrue(~Bool(False))
        self.assertIsInstance(~Bool(True), Bool)

        a = Bool(1)
        a &= 0
        self.assertEqual(a, 0)
        a |= 1
        self.assertEqual(a, 1)
        a ^= 1
        self.assertEqual(a, 0)
        self.assertIsInstance(a, Bool)

    def test_bool_var(self):
        a = Variable(Bool(True))
        self.assertEqual(a.evaluate(), Bool(True))
        a.assign(Bool(False))
        self.assertEqual(a.evaluate(), Bool(False))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(Int(4)))

    def test_int(self):
        self.assertEqual(Int(1), Int(1))
        self.assertIsInstance(Int(1) == Int(1), Bool)
        self.assertNotEqual(Int(1), Int(2))
        self.assertIsInstance(Int(1) != Int(2), Bool)

        self.assertEqual(Int(1), 1)
        self.assertNotEqual(Int(1), 2)

        a = Int(1)
        self.assertEqual(a, 1)
        a += 4
        self.assertEqual(a, 5)
        a *= 2
        self.assertEqual(a, 10)
        a //= 3
        self.assertEqual(a, 3)
        a -= 1
        self.assertEqual(a, 2)
        a += 8
        self.assertEqual(a, 10)
        a %= 4
        self.assertEqual(a, 2)
        a <<= 3
        self.assertEqual(a, 16)
        a >>= 1
        self.assertEqual(a, 8)
        self.assertIsInstance(a, Int)

        self.assertEqual(-Int(4), -4)
        self.assertEqual(~Int(4), ~4)

        b = Int(0xaaaa)
        b |= Int(0x55)
        self.assertEqual(b, 0xaaff)
        b &= Int(0xa5ff)
        self.assertEqual(b, 0xa0ff)
        b ^= Int(0x0050)
        self.assertEqual(b, 0xa0af)
        self.assertIsInstance(a, Int)

        self.assertTrue(Int(4) > Int(1))
        self.assertFalse(Int(4) > Int(4))
        self.assertFalse(Int(1) > Int(4))
        self.assertIsInstance(Int(4) > Int(1), Bool)

        self.assertTrue(Int(4) >= Int(1))
        self.assertTrue(Int(4) >= Int(4))
        self.assertFalse(Int(1) >= Int(4))
        self.assertIsInstance(Int(4) >= Int(1), Bool)

        self.assertFalse(Int(4) < Int(1))
        self.assertFalse(Int(4) < Int(4))
        self.assertTrue(Int(1) < Int(4))
        self.assertIsInstance(Int(4) < Int(1), Bool)

        self.assertFalse(Int(4) <= Int(1))
        self.assertTrue(Int(4) <= Int(4))
        self.assertTrue(Int(1) <= Int(4))
        self.assertIsInstance(Int(4) <= Int(1), Bool)

        self.assertRaises(errors.StaplValueError, lambda: Int(True))
        self.assertRaises(errors.StaplValueError, lambda: Int(Bool(True)))
        self.assertRaises(errors.StaplValueError, lambda: Int(False))
        self.assertRaises(errors.StaplValueError, lambda: Int(Bool(False)))

    def test_int_var(self):
        a = Variable(Int(1))
        self.assertEqual(a.evaluate(), Int(1))
        a.assign(Int(3))
        self.assertEqual(a.evaluate(), Int(3))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(Bool(True)))

    def test_any(self):
        self.assertEqual(Any(1), Any(1))
        self.assertIsInstance(Any(1) == Any(1), Bool)
        self.assertNotEqual(Any(1), Any(2))
        self.assertIsInstance(Any(1) != Any(2), Bool)

        self.assertEqual(Any(1), 1)
        self.assertNotEqual(Any(1), 2)

        a = Any(1)
        a += Int(1)
        self.assertEqual(a, 2)
        self.assertIsInstance(a, Int)

        a = Any(0)
        self.assertIsInstance(Bool(a), Bool)
        self.assertIsInstance(Int(a), Int)

        a = Any(1)
        self.assertIsInstance(Bool(a), Bool)
        self.assertIsInstance(Int(a), Int)

        a = Any(2)
        self.assertRaises(errors.StaplValueError, lambda: Bool(a))
        self.assertIsInstance(Int(a), Int)

        self.assertEqual(Any(1), Bool(1))
        self.assertEqual(Any(2), Int(2))
        self.assertNotEqual(Any(1), Bool(0))
        self.assertNotEqual(Any(1), Int(0))

        self.assertEqual(Bool(1), Any(1))
        self.assertEqual(Int(2), Any(2))
        self.assertNotEqual(Bool(1), Any(0))
        self.assertNotEqual(Int(1), Any(0))
        self.assertRaises(errors.StaplValueError, lambda: Bool(1) == Any(2))

    def test_int_array(self):
        a = IntArray([1, 2, 3, 4])
        self.assertEqual(len(a), 4)
        self.assertEqual(a[0], Int(1))
        self.assertEqual(a[1], Int(2))
        self.assertEqual(a[2], Int(3))
        self.assertEqual(a[3], Int(4))
        self.assertIsInstance(a[0], Int)

        b = a[1:2]
        self.assertEqual(len(b), 2)
        self.assertEqual(b[0], Int(2))
        self.assertEqual(b[1], Int(3))

        c = a[3:1]
        self.assertEqual(len(c), 3)
        self.assertEqual(c[0], Int(4))
        self.assertEqual(c[1], Int(3))
        self.assertEqual(c[2], Int(2))

    def test_int_array_var(self):
        a = ArrayVariable(IntArray([1, 2, 3, 4]))
        self.assertEqual(a.evaluate(), IntArray([1, 2, 3, 4]))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(BoolArray("110011")))
        a.assign(IntArray([5, 6, 7, 8]))
        self.assertEqual(a.evaluate(), IntArray([5, 6, 7, 8]))
        a.assign(slice(1, 2), IntArray([9, 10]))
        self.assertEqual(a.evaluate(), IntArray([5, 9, 10, 8]))
        a.assign(3, Int(11))
        self.assertEqual(a.evaluate(), IntArray([5, 9, 10, 11]))
        a.assign(slice(2, 0), IntArray([12, 13, 14]))
        self.assertEqual(a.evaluate(), IntArray([14, 13, 12, 11]))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(slice(2, 0), IntArray([15])))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(1, IntArray([15])))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(slice(2, 0), Int(15)))

    def test_bool_array(self):
        a = BoolArray("101011")
        self.assertEqual(len(a), 6)
        self.assertEqual(a[5], Bool(1))
        self.assertEqual(a[4], Bool(0))
        self.assertEqual(a[3], Bool(1))
        self.assertEqual(a[2], Bool(0))
        self.assertEqual(a[1], Bool(1))
        self.assertEqual(a[0], Bool(1))
        self.assertIsInstance(a[0], Bool)

        b = a[2:1]
        self.assertEqual(len(b), 2)
        self.assertEqual(b[1], Bool(0))
        self.assertEqual(b[0], Bool(1))

        c = a[0:3]
        self.assertEqual(len(c), 4)
        self.assertEqual(c[3], Bool(1))
        self.assertEqual(c[2], Bool(1))
        self.assertEqual(c[1], Bool(0))
        self.assertEqual(c[0], Bool(1))

    def test_bool_array_var(self):
        a = ArrayVariable(BoolArray("101011"))
        self.assertEqual(a.evaluate(), BoolArray("101011"))
        self.assertRaises(errors.StaplValueError, lambda: a.assign(IntArray([1, 2, 3, 4, 5, 6])))
        a.assign(BoolArray("110011"))
        self.assertEqual(a.evaluate(), BoolArray("110011"))
        a = ArrayVariable(BoolArray("000000"))
        a.assign(slice(4, 3), BoolArray("11"))
        self.assertEqual(a.evaluate(), BoolArray("011000"))
        a.assign(slice(1, 0), BoolArray("10"))
        self.assertEqual(a.evaluate(), BoolArray("011010"))
        a.assign(3, Bool(0))
        self.assertEqual(a.evaluate(), BoolArray("010010"))
        a.assign(slice(0, 2), BoolArray("001"))
        self.assertEqual(a.evaluate(), BoolArray("010100"))
        a.assign(BoolArray("01"))
        self.assertEqual(a.evaluate(), BoolArray("000001"))
        a.assign(BoolArray("1111111111110"))
        self.assertEqual(a.evaluate(), BoolArray("111110"))
        a.assign(slice(5, 4), BoolArray("100"))
        self.assertEqual(a.evaluate(), BoolArray("001110"))
        a.assign(slice(2, 0), BoolArray("1"))
        self.assertEqual(a.evaluate(), BoolArray("001001"))

if __name__ == '__main__':
    unittest.main()

