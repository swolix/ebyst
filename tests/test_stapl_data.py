#!/usr/bin/env python3
import unittest
from ebyst.stapl.data import Int, Bool, Any

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

        self.assertRaises(ValueError, lambda: Int(True))
        self.assertRaises(ValueError, lambda: Int(Bool(True)))
        self.assertRaises(ValueError, lambda: Int(False))
        self.assertRaises(ValueError, lambda: Int(Bool(False)))

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
        self.assertRaises(ValueError, lambda: Bool(a))
        self.assertIsInstance(Int(a), Int)

        self.assertEqual(Any(1), Bool(1))
        self.assertEqual(Any(2), Int(2))
        self.assertNotEqual(Any(1), Bool(0))
        self.assertNotEqual(Any(1), Int(0))

        self.assertEqual(Bool(1), Any(1))
        self.assertEqual(Int(2), Any(2))
        self.assertNotEqual(Bool(1), Any(0))
        self.assertNotEqual(Int(1), Any(0))
        self.assertRaises(ValueError, lambda: Bool(1) == Any(2))

if __name__ == '__main__':
    unittest.main()

