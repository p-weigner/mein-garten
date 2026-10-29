import unittest
from tools.live_test import norm, exact
class TestIdentitaet(unittest.TestCase):
 def test_exact(self): self.assertTrue(exact("Hydrangea macrophylla","Hydrangea macrophylla","species"))
 def test_falsche_art(self): self.assertFalse(exact("Hydrangea paniculata","Hydrangea macrophylla","species"))
 def test_gattung_ist_nicht_art(self): self.assertFalse(exact("Hydrangea macrophylla","Hydrangea macrophylla","genus"))
 def test_hybrid(self): self.assertTrue(exact("Fragaria × ananassa","Fragaria x ananassa","species"))
 def test_umlaute(self): self.assertEqual(norm("Grüne Pflanze"),"grüne pflanze")
if __name__=="__main__":unittest.main()
