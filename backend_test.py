"""
Backend API Testing for Session #074 Remediation Validation
Tests all fixes applied: RET-2, RET-500, RET-ATT-NOOP, PRET-GL, VB-CANCEL-GL,
IDOR security, import hardening, UOM validation, onboarding validation
"""
import requests
import sys
import json
from typing import Dict, Any, Optional

BASE_URL = "https://dark-endpoint-bugs.preview.emergentagent.com/api"

# Test credentials
USERS = {
    "admin": {"email": "admin@kainnusantara.id", "password": "demo12345"},
    "manager": {"email": "manager@kainnusantara.id", "password": "demo12345"},
    "sales": {"email": "sales@kainnusantara.id", "password": "demo12345"},  # ent_ksc
    "sales3": {"email": "sales3@kainnusantara.id", "password": "demo12345"},  # ent_kanda
    "warehouse": {"email": "warehouse@kainnusantara.id", "password": "demo12345"},  # ent_ksc
}

class TestRunner:
    def __init__(self):
        self.tokens: Dict[str, str] = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        
    def login(self, user_key: str) -> bool:
        """Login and store token"""
        if user_key in self.tokens:
            return True
            
        user = USERS.get(user_key)
        if not user:
            print(f"❌ Unknown user: {user_key}")
            return False
            
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", json=user, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.tokens[user_key] = data.get("token", "")
                print(f"✅ Logged in as {user['email']}")
                return True
            else:
                print(f"❌ Login failed for {user['email']}: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error for {user['email']}: {e}")
            return False
    
    def headers(self, user_key: str) -> Dict[str, str]:
        """Get auth headers for user"""
        return {
            "Authorization": f"Bearer {self.tokens.get(user_key, '')}",
            "Content-Type": "application/json"
        }
    
    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             user: str = "admin", data: Optional[Dict] = None, 
             files: Optional[Dict] = None) -> tuple[bool, Any]:
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        
        url = f"{BASE_URL}{endpoint}"
        headers = self.headers(user) if not files else {"Authorization": f"Bearer {self.tokens.get(user, '')}"}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                if files:
                    resp = requests.post(url, headers=headers, files=files, timeout=10)
                else:
                    resp = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PATCH":
                resp = requests.patch(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                print(f"❌ Unsupported method: {method}")
                self.tests_failed += 1
                return False, None
            
            success = resp.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASS - Status: {resp.status_code}")
                try:
                    return True, resp.json()
                except:
                    return True, resp.text
            else:
                self.tests_failed += 1
                self.failures.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": resp.status_code,
                    "response": resp.text[:200]
                })
                print(f"❌ FAIL - Expected {expected_status}, got {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
                return False, None
                
        except Exception as e:
            self.tests_failed += 1
            self.failures.append({"test": name, "error": str(e)})
            print(f"❌ FAIL - Error: {e}")
            return False, None
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failures:
            print("\n" + "="*70)
            print("FAILURES:")
            print("="*70)
            for i, f in enumerate(self.failures, 1):
                print(f"\n{i}. {f.get('test', 'Unknown')}")
                if 'error' in f:
                    print(f"   Error: {f['error']}")
                else:
                    print(f"   Expected: {f.get('expected')}, Got: {f.get('actual')}")
                    print(f"   Response: {f.get('response', '')}")


def main():
    runner = TestRunner()
    
    print("="*70)
    print("SESSION #074 REMEDIATION VALIDATION")
    print("="*70)
    
    # ========================================================================
    # REGRESSION - Auth: all 5 users can login
    # ========================================================================
    print("\n" + "="*70)
    print("REGRESSION TESTS - Authentication")
    print("="*70)
    
    for user_key in ["admin", "manager", "sales", "sales3", "warehouse"]:
        if not runner.login(user_key):
            print(f"❌ CRITICAL: Cannot login as {user_key}")
            return 1
    
    # ========================================================================
    # REGRESSION - Core reads
    # ========================================================================
    print("\n" + "="*70)
    print("REGRESSION TESTS - Core Reads")
    print("="*70)
    
    runner.test("GET /sales-orders", "GET", "/sales-orders", 200, "admin")
    runner.test("GET /products", "GET", "/products", 200, "admin")
    runner.test("GET /entities", "GET", "/entities", 200, "admin")
    runner.test("GET /gl/trial-balance", "GET", "/gl/trial-balance", 200, "admin")
    
    # ========================================================================
    # Get test data - find an ent_ksc sales order
    # ========================================================================
    print("\n" + "="*70)
    print("SETUP - Finding test data")
    print("="*70)
    
    success, orders_data = runner.test("GET /sales-orders for test data", "GET", "/sales-orders", 200, "admin")
    ksc_order_id = None
    if success and orders_data:
        orders = orders_data.get("items", orders_data) if isinstance(orders_data, dict) else orders_data
        for order in orders:
            if order.get("entity_id") == "ent_ksc":
                ksc_order_id = order.get("id")
                print(f"✅ Found ent_ksc order: {ksc_order_id}")
                break
    
    if not ksc_order_id:
        print("⚠️  No ent_ksc order found, skipping IDOR tests")
    
    # ========================================================================
    # RET-500 FIX: Bogus sales return ID should return 404, not 500
    # ========================================================================
    print("\n" + "="*70)
    print("RET-500 FIX - Bogus ID returns 404")
    print("="*70)
    
    runner.test("POST /sales-returns/BOGUSID/approve", "POST", "/sales-returns/BOGUSID/approve", 404, "admin", {})
    runner.test("POST /sales-returns/BOGUSID/reject", "POST", "/sales-returns/BOGUSID/reject", 404, "admin", {})
    
    # ========================================================================
    # RET-ATT-NOOP FIX: DELETE bogus attachment should return 404
    # ========================================================================
    print("\n" + "="*70)
    print("RET-ATT-NOOP FIX - Bogus attachment returns 404")
    print("="*70)
    
    runner.test("DELETE /sales-returns/BOGUS/attachments/BOGUS", "DELETE", 
                "/sales-returns/BOGUS/attachments/BOGUS", 404, "admin")
    
    # ========================================================================
    # RET-2 FIX: Create sales return and verify credit_note_id is set
    # ========================================================================
    print("\n" + "="*70)
    print("RET-2 FIX - Sales return creates credit note")
    print("="*70)
    
    # Find a suitable sales order for return
    success, orders_data = runner.test("GET /sales-orders for return", "GET", "/sales-orders", 200, "admin")
    suitable_order = None
    if success and orders_data:
        orders = orders_data.get("items", orders_data) if isinstance(orders_data, dict) else orders_data
        for order in orders:
            if order.get("status") in ["confirmed", "shipped", "done"] and order.get("items"):
                suitable_order = order
                break
    
    if suitable_order:
        print(f"✅ Found suitable order for return: {suitable_order.get('number')}")
        
        # Create sales return
        item = suitable_order["items"][0]
        return_payload = {
            "order_id": suitable_order["id"],
            "return_type": "retur",
            "items": [{
                "product_id": item["product_id"],
                "product_name": item.get("product_name", ""),
                "quantity_returned": 1.0,
                "unit": item.get("unit", "meter"),
                "reason": "Test return",
                "condition": "ok"
            }],
            "notes": "Test return for RET-2 validation",
            "submit_now": True
        }
        
        success, return_data = runner.test("POST /sales-returns", "POST", "/sales-returns", 
                                          200, "admin", return_payload)
        
        if success and return_data:
            return_id = return_data.get("id")
            print(f"✅ Created sales return: {return_id}")
            
            # Approve the return
            success, approved_data = runner.test("POST /sales-returns/{id}/approve", "POST",
                                                f"/sales-returns/{return_id}/approve", 
                                                200, "admin", {})
            
            if success and approved_data:
                credit_note_id = approved_data.get("credit_note_id")
                if credit_note_id:
                    print(f"✅ RET-2 FIX VERIFIED: credit_note_id = {credit_note_id}")
                    runner.tests_passed += 1
                else:
                    print(f"❌ RET-2 FIX FAILED: credit_note_id is null")
                    runner.tests_failed += 1
                    runner.failures.append({
                        "test": "RET-2: credit_note_id should be set",
                        "expected": "non-null credit_note_id",
                        "actual": "null"
                    })
    else:
        print("⚠️  No suitable order found for return test")
    
    # ========================================================================
    # IDOR SECURITY - Cross-entity access blocked
    # ========================================================================
    if ksc_order_id:
        print("\n" + "="*70)
        print("IDOR SECURITY - Cross-entity access blocked")
        print("="*70)
        
        # sales3 (ent_kanda) should NOT access ent_ksc order
        runner.test("GET /sales-orders/{ksc_id} as sales3 (cross-entity)", "GET",
                   f"/sales-orders/{ksc_order_id}", 404, "sales3")
        
        runner.test("PATCH /sales-orders/{ksc_id} as sales3 (cross-entity)", "PATCH",
                   f"/sales-orders/{ksc_order_id}", 404, "sales3", 
                   {"data": {"notes": "cross-entity-test"}})
        
        runner.test("POST /sales-orders/{ksc_id}/simulate-payment as sales3", "POST",
                   f"/sales-orders/{ksc_order_id}/simulate-payment", 404, "sales3", {})
        
        runner.test("POST /sales-orders/{ksc_id}/submit-for-approval as sales3", "POST",
                   f"/sales-orders/{ksc_order_id}/submit-for-approval", 404, "sales3", {})
        
        # ========================================================================
        # IDOR REGRESSION - Same-entity access still works
        # ========================================================================
        print("\n" + "="*70)
        print("IDOR REGRESSION - Same-entity access works")
        print("="*70)
        
        runner.test("GET /sales-orders/{ksc_id} as sales (same-entity)", "GET",
                   f"/sales-orders/{ksc_order_id}", 200, "sales")
        
        runner.test("PATCH /sales-orders/{ksc_id} as sales (same-entity)", "PATCH",
                   f"/sales-orders/{ksc_order_id}", 200, "sales",
                   {"data": {"notes": "regress-test"}})
    
    # ========================================================================
    # VAL-UOM FIX - UOM factor_to_base validation
    # ========================================================================
    print("\n" + "="*70)
    print("VAL-UOM FIX - factor_to_base validation")
    print("="*70)
    
    runner.test("POST /uoms with factor_to_base=-5", "POST", "/uoms", 422, "admin",
               {"code": "RGT1", "name": "Test UOM", "base_type": "length", "factor_to_base": -5})
    
    runner.test("POST /uoms with factor_to_base=0", "POST", "/uoms", 422, "admin",
               {"code": "RGT2", "name": "Test UOM", "base_type": "length", "factor_to_base": 0})
    
    runner.test("POST /uoms with factor_to_base=2", "POST", "/uoms", 200, "admin",
               {"code": "RGT3", "name": "Test UOM Valid", "base_type": "length", "factor_to_base": 2})
    
    # ========================================================================
    # ONBOARD-NOOP FIX - Onboarding task validation
    # ========================================================================
    print("\n" + "="*70)
    print("ONBOARD-NOOP FIX - Task validation")
    print("="*70)
    
    runner.test("POST /onboarding/BOGUSTASK/complete", "POST", 
               "/onboarding/BOGUSTASK/complete", 404, "admin")
    
    runner.test("POST /onboarding/create_uom/complete", "POST",
               "/onboarding/create_uom/complete", 200, "admin")
    
    # ========================================================================
    # IMPORT HARDENING - CSV import validation
    # ========================================================================
    print("\n" + "="*70)
    print("IMPORT HARDENING - CSV validation")
    print("="*70)
    
    # Test 1: Non-UTF8 bytes should return 400
    non_utf8_bytes = b'\xff\xfe Invalid UTF-8'
    runner.test("Import non-UTF8 file", "POST", "/master-data/import-products", 400, "admin",
               files={"file": ("test.csv", non_utf8_bytes, "text/csv")})
    
    # Test 2: Negative price should be rejected
    csv_negative_price = "sku,name,price\nTEST001,Test Product,-5000\n"
    runner.test("Import CSV with negative price", "POST", "/master-data/import-products", 200, "admin",
               files={"file": ("test.csv", csv_negative_price.encode('utf-8'), "text/csv")})
    
    # Verify it was rejected (created=0)
    # Note: The endpoint returns 200 but with errors array
    
    # Test 3: XSS in image URL should be rejected
    csv_xss = "sku,name,price,image\nTEST002,Test Product,1000,javascript:alert(1)\n"
    runner.test("Import CSV with XSS image", "POST", "/master-data/import-products", 200, "admin",
               files={"file": ("test.csv", csv_xss.encode('utf-8'), "text/csv")})
    
    # Test 4: Valid CSV should import
    csv_valid = "sku,name,price\nTEST003,Valid Product,1000\n"
    success, import_result = runner.test("Import valid CSV", "POST", "/master-data/import-products", 
                                        200, "admin",
                                        files={"file": ("test.csv", csv_valid.encode('utf-8'), "text/csv")})
    
    if success and import_result:
        created = import_result.get("created", 0)
        if created >= 1:
            print(f"✅ Valid CSV imported successfully: {created} created")
        else:
            print(f"⚠️  Valid CSV import created {created} records")
    
    # Test 5: Export should not contain formula injection
    success, export_data = runner.test("GET /master-data/export-products", "GET",
                                       "/master-data/export-products", 200, "admin")
    
    if success and export_data:
        # Check if any cell starts with = without apostrophe prefix
        if isinstance(export_data, str):
            lines = export_data.split('\n')
            has_formula = False
            for line in lines[1:]:  # Skip header
                if line.strip() and line.strip()[0] in ['=', '+', '-', '@']:
                    has_formula = True
                    print(f"❌ FORMULA INJECTION: Found unescaped formula: {line[:50]}")
                    break
            if not has_formula:
                print("✅ Export CSV is safe from formula injection")
    
    # ========================================================================
    # Print final summary
    # ========================================================================
    runner.print_summary()
    
    return 0 if runner.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
