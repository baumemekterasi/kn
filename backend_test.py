"""
Backend API Testing for Financial Statements Module (FINANCE) + Stock Analytics (Fase 5)
Tests: Income Statement, Balance Sheet, CSV exports, entity scoping, GL regression, Stock Analytics
"""
import requests
import sys
from datetime import datetime

BASE_URL = "https://epic-cannon-6.preview.emergentagent.com/api"
LOGIN_EMAIL = "admin@kainnusantara.id"
LOGIN_PASSWORD = "demo12345"

class FinancialStatementsAPITester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def log(self, message, level="INFO"):
        """Log test messages"""
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️"
        }.get(level, "•")
        print(f"{prefix} {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, headers=None, check_csv=False):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing: {name}", "INFO")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, params=params, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=req_headers, params=params, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, params=params, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"PASSED - {name} (Status: {response.status_code})", "SUCCESS")
                
                # Additional checks for CSV
                if check_csv:
                    content_type = response.headers.get('Content-Type', '')
                    content_disp = response.headers.get('Content-Disposition', '')
                    if 'text/csv' in content_type and 'attachment' in content_disp:
                        self.log(f"  CSV headers valid: Content-Type={content_type}, Content-Disposition={content_disp}", "SUCCESS")
                    else:
                        self.log(f"  CSV headers invalid: Content-Type={content_type}, Content-Disposition={content_disp}", "WARN")
                
                return True, response
            else:
                self.tests_failed += 1
                self.failed_tests.append(name)
                self.log(f"FAILED - {name} (Expected {expected_status}, got {response.status_code})", "FAIL")
                try:
                    error_detail = response.json()
                    self.log(f"  Error: {error_detail}", "FAIL")
                except:
                    self.log(f"  Response: {response.text[:200]}", "FAIL")
                return False, response

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            self.log(f"FAILED - {name} (Exception: {str(e)})", "FAIL")
            return False, None

    def test_login(self):
        """Test login and get token"""
        self.log("\n=== AUTHENTICATION ===", "INFO")
        success, response = self.run_test(
            "Login",
            "POST",
            "/auth/login",
            200,
            data={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
        )
        if success and response:
            try:
                data = response.json()
                self.token = data.get('token')
                if self.token:
                    self.log(f"  Token obtained: {self.token[:20]}...", "SUCCESS")
                    return True
                else:
                    self.log("  No token in response", "FAIL")
                    return False
            except:
                self.log("  Failed to parse login response", "FAIL")
                return False
        return False

    def test_income_statement_basic(self):
        """Test Income Statement without filters"""
        self.log("\n=== INCOME STATEMENT - BASIC ===", "INFO")
        success, response = self.run_test(
            "Income Statement (no filters)",
            "GET",
            "/finance/income-statement",
            200
        )
        if success and response:
            try:
                data = response.json()
                # Check structure
                required_fields = ['sections', 'revenue_total', 'gross_profit', 'net_income', 'gross_margin', 'net_margin']
                missing = [f for f in required_fields if f not in data]
                if missing:
                    self.log(f"  Missing fields: {missing}", "WARN")
                else:
                    self.log(f"  Structure valid: revenue={data.get('revenue_total')}, net_income={data.get('net_income')}", "SUCCESS")
                
                # Check sections
                sections = data.get('sections', [])
                section_keys = [s.get('key') for s in sections]
                expected_sections = ['revenue', 'cogs', 'opex']
                if all(k in section_keys for k in expected_sections):
                    self.log(f"  Sections present: {section_keys}", "SUCCESS")
                else:
                    self.log(f"  Sections: {section_keys} (expected: {expected_sections})", "WARN")
                
                return True
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def test_income_statement_with_filters(self):
        """Test Income Statement with date filters"""
        self.log("\n=== INCOME STATEMENT - WITH FILTERS ===", "INFO")
        success, response = self.run_test(
            "Income Statement (with start & end)",
            "GET",
            "/finance/income-statement",
            200,
            params={"start": "2026-01-01", "end": "2026-12-31"}
        )
        if success and response:
            try:
                data = response.json()
                period = data.get('period', {})
                self.log(f"  Period: {period.get('start')} to {period.get('end')}", "SUCCESS")
                return True
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def test_balance_sheet_single(self):
        """Test Balance Sheet single period"""
        self.log("\n=== BALANCE SHEET - SINGLE PERIOD ===", "INFO")
        success, response = self.run_test(
            "Balance Sheet (single period, as_of)",
            "GET",
            "/finance/balance-sheet",
            200,
            params={"as_of": "2026-12-31"}
        )
        if success and response:
            try:
                data = response.json()
                # Check structure
                required_fields = ['assets', 'liabilities', 'equity', 'assets_total', 'liabilities_total', 
                                   'equity_total', 'liabilities_equity_total', 'balanced']
                missing = [f for f in required_fields if f not in data]
                if missing:
                    self.log(f"  Missing fields: {missing}", "WARN")
                else:
                    self.log(f"  Structure valid", "SUCCESS")
                
                # Check balanced
                balanced = data.get('balanced')
                assets = data.get('assets_total', 0)
                liab_eq = data.get('liabilities_equity_total', 0)
                self.log(f"  Assets: {assets}, Liab+Equity: {liab_eq}, Balanced: {balanced}", "SUCCESS" if balanced else "WARN")
                
                # Check comparative flag
                comparative = data.get('comparative', False)
                if not comparative:
                    self.log(f"  Comparative mode: False (as expected)", "SUCCESS")
                else:
                    self.log(f"  Comparative mode: True (unexpected)", "WARN")
                
                return True
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def test_balance_sheet_comparative(self):
        """Test Balance Sheet comparative mode"""
        self.log("\n=== BALANCE SHEET - COMPARATIVE MODE ===", "INFO")
        success, response = self.run_test(
            "Balance Sheet (comparative with compare_as_of)",
            "GET",
            "/finance/balance-sheet",
            200,
            params={"as_of": "2026-12-31", "compare_as_of": "2026-06-30"}
        )
        if success and response:
            try:
                data = response.json()
                # Check comparative flag
                comparative = data.get('comparative', False)
                if comparative:
                    self.log(f"  Comparative mode: True", "SUCCESS")
                else:
                    self.log(f"  Comparative mode: False (expected True)", "FAIL")
                    return False
                
                # Check compare block
                compare = data.get('compare', {})
                if compare:
                    self.log(f"  Compare block present: assets={compare.get('assets_total')}, balanced={compare.get('balanced')}", "SUCCESS")
                else:
                    self.log(f"  Compare block missing", "WARN")
                
                # Check delta block
                delta = data.get('delta', {})
                if delta:
                    self.log(f"  Delta block present: assets={delta.get('assets_total')}", "SUCCESS")
                else:
                    self.log(f"  Delta block missing", "WARN")
                
                # Check equity compare fields
                equity = data.get('equity', {})
                if 'compare_current_earnings' in equity:
                    self.log(f"  Equity compare_current_earnings: {equity.get('compare_current_earnings')}", "SUCCESS")
                else:
                    self.log(f"  Equity compare_current_earnings missing", "WARN")
                
                # Check line-level compare_amount and delta
                assets_sections = data.get('assets', {}).get('sections', [])
                if assets_sections:
                    first_section = assets_sections[0]
                    lines = first_section.get('lines', [])
                    if lines:
                        first_line = lines[0]
                        if 'compare_amount' in first_line and 'delta' in first_line:
                            self.log(f"  Line-level compare_amount & delta present", "SUCCESS")
                        else:
                            self.log(f"  Line-level compare_amount or delta missing", "WARN")
                
                return True
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def test_income_statement_csv_export(self):
        """Test Income Statement CSV export"""
        self.log("\n=== INCOME STATEMENT - CSV EXPORT ===", "INFO")
        success, response = self.run_test(
            "Income Statement CSV export",
            "GET",
            "/finance/income-statement/export.csv",
            200,
            params={"start": "2026-01-01", "end": "2026-12-31"},
            check_csv=True
        )
        if success and response:
            try:
                # Check if response is CSV
                content = response.text
                if 'Laba-Rugi' in content or 'Income Statement' in content:
                    self.log(f"  CSV content valid (length: {len(content)} bytes)", "SUCCESS")
                    return True
                else:
                    self.log(f"  CSV content unexpected: {content[:100]}", "WARN")
            except Exception as e:
                self.log(f"  Failed to parse CSV: {e}", "FAIL")
        return False

    def test_balance_sheet_csv_export_single(self):
        """Test Balance Sheet CSV export (single period)"""
        self.log("\n=== BALANCE SHEET - CSV EXPORT (SINGLE) ===", "INFO")
        success, response = self.run_test(
            "Balance Sheet CSV export (single period)",
            "GET",
            "/finance/balance-sheet/export.csv",
            200,
            params={"as_of": "2026-12-31"},
            check_csv=True
        )
        if success and response:
            try:
                content = response.text
                if 'Neraca' in content or 'Balance Sheet' in content:
                    self.log(f"  CSV content valid (length: {len(content)} bytes)", "SUCCESS")
                    # Check no comparative columns
                    if 'Pembanding' not in content and 'Delta' not in content:
                        self.log(f"  No comparative columns (as expected)", "SUCCESS")
                    else:
                        self.log(f"  Comparative columns found (unexpected)", "WARN")
                    return True
                else:
                    self.log(f"  CSV content unexpected: {content[:100]}", "WARN")
            except Exception as e:
                self.log(f"  Failed to parse CSV: {e}", "FAIL")
        return False

    def test_balance_sheet_csv_export_comparative(self):
        """Test Balance Sheet CSV export (comparative)"""
        self.log("\n=== BALANCE SHEET - CSV EXPORT (COMPARATIVE) ===", "INFO")
        success, response = self.run_test(
            "Balance Sheet CSV export (comparative)",
            "GET",
            "/finance/balance-sheet/export.csv",
            200,
            params={"as_of": "2026-12-31", "compare_as_of": "2026-06-30"},
            check_csv=True
        )
        if success and response:
            try:
                content = response.text
                if 'Neraca' in content or 'Balance Sheet' in content:
                    self.log(f"  CSV content valid (length: {len(content)} bytes)", "SUCCESS")
                    # Check comparative columns
                    if 'Pembanding' in content and 'Delta' in content:
                        self.log(f"  Comparative columns present (Pembanding & Delta)", "SUCCESS")
                    else:
                        self.log(f"  Comparative columns missing", "WARN")
                    return True
                else:
                    self.log(f"  CSV content unexpected: {content[:100]}", "WARN")
            except Exception as e:
                self.log(f"  Failed to parse CSV: {e}", "FAIL")
        return False

    def test_entity_scoping_param(self):
        """Test entity scoping via entity_id param"""
        self.log("\n=== ENTITY SCOPING - PARAM ===", "INFO")
        success, response = self.run_test(
            "Income Statement with entity_id param",
            "GET",
            "/finance/income-statement",
            200,
            params={"entity_id": "all", "start": "2026-01-01", "end": "2026-12-31"}
        )
        if success:
            self.log(f"  Entity scoping via param works", "SUCCESS")
            return True
        return False

    def test_entity_scoping_header(self):
        """Test entity scoping via X-Entity-Id header"""
        self.log("\n=== ENTITY SCOPING - HEADER ===", "INFO")
        success, response = self.run_test(
            "Balance Sheet with X-Entity-Id header",
            "GET",
            "/finance/balance-sheet",
            200,
            params={"as_of": "2026-12-31"},
            headers={"X-Entity-Id": "all"}
        )
        if success:
            self.log(f"  Entity scoping via header works", "SUCCESS")
            return True
        return False

    def test_gl_regression_trial_balance(self):
        """Test GL regression: trial balance still works"""
        self.log("\n=== GL REGRESSION - TRIAL BALANCE ===", "INFO")
        success, response = self.run_test(
            "GL Trial Balance",
            "GET",
            "/gl/trial-balance",
            200
        )
        if success and response:
            try:
                data = response.json()
                if 'rows' in data and 'balanced' in data:
                    balanced = data.get('balanced')
                    total_debit = data.get('total_debit', 0)
                    total_credit = data.get('total_credit', 0)
                    self.log(f"  Trial Balance: Debit={total_debit}, Credit={total_credit}, Balanced={balanced}", "SUCCESS" if balanced else "WARN")
                    return True
                else:
                    self.log(f"  Trial Balance structure invalid", "WARN")
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def test_gl_regression_summary(self):
        """Test GL regression: summary still works"""
        self.log("\n=== GL REGRESSION - SUMMARY ===", "INFO")
        success, response = self.run_test(
            "GL Summary",
            "GET",
            "/gl/summary",
            200
        )
        if success and response:
            try:
                data = response.json()
                if 'journal_count' in data and 'balanced' in data:
                    self.log(f"  GL Summary: journals={data.get('journal_count')}, balanced={data.get('balanced')}", "SUCCESS")
                    return True
                else:
                    self.log(f"  GL Summary structure invalid", "WARN")
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def test_gl_regression_journal(self):
        """Test GL regression: journal entries still work"""
        self.log("\n=== GL REGRESSION - JOURNAL ENTRIES ===", "INFO")
        success, response = self.run_test(
            "GL Journal Entries",
            "GET",
            "/gl/journal",
            200,
            params={"limit": 10}
        )
        if success and response:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.log(f"  Journal Entries: {len(data)} entries returned", "SUCCESS")
                    return True
                else:
                    self.log(f"  Journal Entries: unexpected format", "WARN")
            except Exception as e:
                self.log(f"  Failed to parse response: {e}", "FAIL")
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*60, "INFO")
        self.log(f"Total Tests: {self.tests_run}", "INFO")
        self.log(f"Passed: {self.tests_passed}", "SUCCESS")
        self.log(f"Failed: {self.tests_failed}", "FAIL" if self.tests_failed > 0 else "INFO")
        
        if self.tests_failed > 0:
            self.log("\nFailed Tests:", "FAIL")
            for test in self.failed_tests:
                self.log(f"  - {test}", "FAIL")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "SUCCESS" if success_rate >= 80 else "WARN")
        self.log("="*60, "INFO")
        
        return 0 if self.tests_failed == 0 else 1



class StockAnalyticsAPITester:
    """Test Stock Analytics endpoint (Fase 5)"""
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def log(self, message, level="INFO"):
        """Log test messages"""
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️"
        }.get(level, "•")
        print(f"{prefix} {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, headers=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing: {name}", "INFO")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, params=params, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"PASSED - {name} (Status: {response.status_code})", "SUCCESS")
                return True, response
            else:
                self.tests_failed += 1
                self.failed_tests.append(name)
                self.log(f"FAILED - {name} (Expected {expected_status}, got {response.status_code})", "FAIL")
                try:
                    error_detail = response.json()
                    self.log(f"  Error: {error_detail}", "FAIL")
                except:
                    self.log(f"  Response: {response.text[:200]}", "FAIL")
                return False, response

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            self.log(f"FAILED - {name} (Exception: {str(e)})", "FAIL")
            return False, None

    def test_login(self):
        """Test login and get token"""
        self.log("\n=== AUTHENTICATION ===", "INFO")
        success, response = self.run_test(
            "Login",
            "POST",
            "/auth/login",
            200,
            data={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
        )
        if success and response:
            try:
                data = response.json()
                self.token = data.get('token')
                if self.token:
                    self.log(f"Token obtained successfully", "SUCCESS")
                    return True
            except:
                pass
        self.log("Failed to obtain token", "FAIL")
        return False

    def test_stock_analytics_basic(self):
        """Test basic stock analytics endpoint with entity_id=all"""
        self.log("\n=== STOCK ANALYTICS - BASIC ===", "INFO")
        success, response = self.run_test(
            "Stock Analytics - Basic (entity_id=all)",
            "GET",
            "/inventory/stock-analytics",
            200,
            params={"entity_id": "all"},
            headers={"X-Entity-Id": "all"}
        )
        
        if success and response:
            try:
                data = response.json()
                
                # Verify structure
                required_keys = ['generated_at', 'thresholds', 'filters', 'summary', 'rows']
                for key in required_keys:
                    if key not in data:
                        self.log(f"  Missing key: {key}", "FAIL")
                        return False
                
                # Verify thresholds
                thresholds = data.get('thresholds', {})
                if thresholds.get('fast_max_days') != 30:
                    self.log(f"  Threshold fast_max_days: expected 30, got {thresholds.get('fast_max_days')}", "WARN")
                if thresholds.get('slow_max_days') != 90:
                    self.log(f"  Threshold slow_max_days: expected 90, got {thresholds.get('slow_max_days')}", "WARN")
                if thresholds.get('velocity_window_days') != 90:
                    self.log(f"  Threshold velocity_window_days: expected 90, got {thresholds.get('velocity_window_days')}", "WARN")
                
                # Verify summary structure
                summary = data.get('summary', {})
                sku_count = summary.get('sku_count', 0)
                by_class = summary.get('by_class', {})
                
                self.log(f"  SKU count: {sku_count}", "INFO")
                self.log(f"  Fast: {by_class.get('fast', {}).get('count', 0)}", "INFO")
                self.log(f"  Slow: {by_class.get('slow', {}).get('count', 0)}", "INFO")
                self.log(f"  Dead: {by_class.get('dead', {}).get('count', 0)}", "INFO")
                self.log(f"  Never sold: {summary.get('never_sold_skus', 0)}", "INFO")
                
                # Verify expected seed data (sku_count=11, fast=3, slow=8, dead=0, never_sold=6)
                # Note: These are expected values from seed data, may vary
                if sku_count == 11:
                    self.log(f"  ✓ SKU count matches expected (11)", "SUCCESS")
                else:
                    self.log(f"  ⚠ SKU count: expected 11, got {sku_count}", "WARN")
                
                fast_count = by_class.get('fast', {}).get('count', 0)
                slow_count = by_class.get('slow', {}).get('count', 0)
                dead_count = by_class.get('dead', {}).get('count', 0)
                never_sold = summary.get('never_sold_skus', 0)
                
                if fast_count == 3:
                    self.log(f"  ✓ Fast count matches expected (3)", "SUCCESS")
                else:
                    self.log(f"  ⚠ Fast count: expected 3, got {fast_count}", "WARN")
                
                if slow_count == 8:
                    self.log(f"  ✓ Slow count matches expected (8)", "SUCCESS")
                else:
                    self.log(f"  ⚠ Slow count: expected 8, got {slow_count}", "WARN")
                
                if dead_count == 0:
                    self.log(f"  ✓ Dead count matches expected (0)", "SUCCESS")
                else:
                    self.log(f"  ⚠ Dead count: expected 0, got {dead_count}", "WARN")
                
                if never_sold == 6:
                    self.log(f"  ✓ Never sold count matches expected (6)", "SUCCESS")
                else:
                    self.log(f"  ⚠ Never sold count: expected 6, got {never_sold}", "WARN")
                
                # Verify internal consistency: by_class counts == rows grouped by classification
                rows = data.get('rows', [])
                row_fast = sum(1 for r in rows if r.get('classification') == 'fast')
                row_slow = sum(1 for r in rows if r.get('classification') == 'slow')
                row_dead = sum(1 for r in rows if r.get('classification') == 'dead')
                
                if row_fast == fast_count and row_slow == slow_count and row_dead == dead_count:
                    self.log(f"  ✓ Internal consistency: by_class counts match row classifications", "SUCCESS")
                else:
                    self.log(f"  ✗ Inconsistency: by_class ({fast_count}/{slow_count}/{dead_count}) vs rows ({row_fast}/{row_slow}/{row_dead})", "FAIL")
                
                return True
            except Exception as e:
                self.log(f"  Error parsing response: {str(e)}", "FAIL")
                return False
        return False

    def test_warehouse_filter(self):
        """Test warehouse filter"""
        self.log("\n=== STOCK ANALYTICS - WAREHOUSE FILTER ===", "INFO")
        
        # First get all warehouses
        success, response = self.run_test(
            "Get Warehouses",
            "GET",
            "/warehouses",
            200
        )
        
        if not success or not response:
            self.log("  Cannot test warehouse filter without warehouse data", "WARN")
            return False
        
        try:
            warehouses = response.json()
            if not warehouses:
                self.log("  No warehouses found", "WARN")
                return False
            
            warehouse_id = warehouses[0].get('id')
            warehouse_name = warehouses[0].get('name', 'Unknown')
            
            self.log(f"  Testing with warehouse: {warehouse_name} ({warehouse_id})", "INFO")
            
            success, response = self.run_test(
                f"Stock Analytics - Warehouse Filter ({warehouse_name})",
                "GET",
                "/inventory/stock-analytics",
                200,
                params={"entity_id": "all", "warehouse_id": warehouse_id},
                headers={"X-Entity-Id": "all"}
            )
            
            if success and response:
                data = response.json()
                filters = data.get('filters', {})
                if filters.get('warehouse_id') == warehouse_id:
                    self.log(f"  ✓ Warehouse filter applied correctly", "SUCCESS")
                    return True
                else:
                    self.log(f"  ✗ Warehouse filter not applied: {filters}", "FAIL")
            return False
        except Exception as e:
            self.log(f"  Error: {str(e)}", "FAIL")
            return False

    def test_category_filter(self):
        """Test category filter"""
        self.log("\n=== STOCK ANALYTICS - CATEGORY FILTER ===", "INFO")
        
        # First get all data to find a category
        success, response = self.run_test(
            "Get Stock Analytics for Category Discovery",
            "GET",
            "/inventory/stock-analytics",
            200,
            params={"entity_id": "all"},
            headers={"X-Entity-Id": "all"}
        )
        
        if not success or not response:
            self.log("  Cannot test category filter", "WARN")
            return False
        
        try:
            data = response.json()
            rows = data.get('rows', [])
            categories = set(r.get('category') for r in rows if r.get('category'))
            
            if not categories:
                self.log("  No categories found in data", "WARN")
                return False
            
            test_category = list(categories)[0]
            self.log(f"  Testing with category: {test_category}", "INFO")
            
            success, response = self.run_test(
                f"Stock Analytics - Category Filter ({test_category})",
                "GET",
                "/inventory/stock-analytics",
                200,
                params={"entity_id": "all", "category": test_category},
                headers={"X-Entity-Id": "all"}
            )
            
            if success and response:
                data = response.json()
                filters = data.get('filters', {})
                rows = data.get('rows', [])
                
                if filters.get('category') == test_category:
                    self.log(f"  ✓ Category filter applied correctly", "SUCCESS")
                    
                    # Verify all rows match the category
                    all_match = all(r.get('category') == test_category for r in rows)
                    if all_match:
                        self.log(f"  ✓ All rows match category filter", "SUCCESS")
                        return True
                    else:
                        self.log(f"  ✗ Some rows don't match category filter", "FAIL")
                else:
                    self.log(f"  ✗ Category filter not applied: {filters}", "FAIL")
            return False
        except Exception as e:
            self.log(f"  Error: {str(e)}", "FAIL")
            return False

    def test_classification_logic(self):
        """Test classification correctness (fast/slow/dead logic)"""
        self.log("\n=== STOCK ANALYTICS - CLASSIFICATION LOGIC ===", "INFO")
        
        success, response = self.run_test(
            "Stock Analytics - Classification Logic",
            "GET",
            "/inventory/stock-analytics",
            200,
            params={"entity_id": "all"},
            headers={"X-Entity-Id": "all"}
        )
        
        if not success or not response:
            return False
        
        try:
            data = response.json()
            rows = data.get('rows', [])
            thresholds = data.get('thresholds', {})
            fast_max = thresholds.get('fast_max_days', 30)
            slow_max = thresholds.get('slow_max_days', 90)
            
            self.log(f"  Checking classification logic (Fast ≤{fast_max}d, Slow ≤{slow_max}d, Dead >{slow_max}d)", "INFO")
            
            errors = []
            for row in rows:
                cls = row.get('classification')
                days_since_sale = row.get('days_since_sale')
                never_sold = row.get('never_sold', False)
                oldest_age = row.get('oldest_age_days', 0)
                sku = row.get('sku', 'Unknown')
                
                # Classification logic from service:
                # - If never sold and would be 'fast', downgrade to 'slow'
                # - Fast: days_since_sale ≤ fast_max
                # - Slow: days_since_sale ≤ slow_max
                # - Dead: days_since_sale > slow_max
                
                if days_since_sale is not None:
                    if days_since_sale <= fast_max:
                        expected = 'fast' if not never_sold else 'slow'
                    elif days_since_sale <= slow_max:
                        expected = 'slow'
                    else:
                        expected = 'dead'
                    
                    if cls != expected:
                        errors.append(f"{sku}: expected {expected}, got {cls} (days_since_sale={days_since_sale}, never_sold={never_sold})")
                else:
                    # No sale, use oldest_age
                    if oldest_age <= fast_max:
                        expected = 'slow'  # Never sold items are downgraded from fast to slow
                    elif oldest_age <= slow_max:
                        expected = 'slow'
                    else:
                        expected = 'dead'
                    
                    if cls != expected:
                        errors.append(f"{sku}: expected {expected}, got {cls} (oldest_age={oldest_age}, never_sold={never_sold})")
            
            if not errors:
                self.log(f"  ✓ All classifications are correct", "SUCCESS")
                return True
            else:
                self.log(f"  ✗ Classification errors found:", "FAIL")
                for err in errors[:5]:  # Show first 5 errors
                    self.log(f"    {err}", "FAIL")
                return False
        except Exception as e:
            self.log(f"  Error: {str(e)}", "FAIL")
            return False

    def test_sold_qty_window(self):
        """Test that sold_qty_window > 0 only for products with sales in velocity window"""
        self.log("\n=== STOCK ANALYTICS - SOLD QTY WINDOW ===", "INFO")
        
        success, response = self.run_test(
            "Stock Analytics - Sold Qty Window",
            "GET",
            "/inventory/stock-analytics",
            200,
            params={"entity_id": "all"},
            headers={"X-Entity-Id": "all"}
        )
        
        if not success or not response:
            return False
        
        try:
            data = response.json()
            rows = data.get('rows', [])
            
            errors = []
            for row in rows:
                sold_qty = row.get('sold_qty_window', 0)
                never_sold = row.get('never_sold', False)
                sku = row.get('sku', 'Unknown')
                
                # If never_sold=True, sold_qty_window should be 0
                if never_sold and sold_qty > 0:
                    errors.append(f"{sku}: never_sold=True but sold_qty_window={sold_qty}")
            
            if not errors:
                self.log(f"  ✓ Sold qty window logic is correct", "SUCCESS")
                return True
            else:
                self.log(f"  ✗ Sold qty window errors found:", "FAIL")
                for err in errors[:5]:
                    self.log(f"    {err}", "FAIL")
                return False
        except Exception as e:
            self.log(f"  Error: {str(e)}", "FAIL")
            return False

    def test_permission_required(self):
        """Test that endpoint requires product:view permission"""
        self.log("\n=== STOCK ANALYTICS - PERMISSION CHECK ===", "INFO")
        
        # Try without token (should fail with 401 or 403)
        url = f"{BASE_URL}/inventory/stock-analytics"
        try:
            response = requests.get(url, params={"entity_id": "all"}, timeout=30)
            if response.status_code in [401, 403]:
                self.log(f"  ✓ Endpoint requires authentication (Status: {response.status_code})", "SUCCESS")
                self.tests_passed += 1
                return True
            else:
                self.log(f"  ✗ Endpoint accessible without auth (Status: {response.status_code})", "FAIL")
                self.tests_failed += 1
                self.failed_tests.append("Permission Check")
                return False
        except Exception as e:
            self.log(f"  Error: {str(e)}", "FAIL")
            self.tests_failed += 1
            self.failed_tests.append("Permission Check")
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("STOCK ANALYTICS TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.failed_tests:
            print("\nFailed Tests:")
            for test in self.failed_tests:
                print(f"  • {test}")
        
        print("="*60)
        return 0 if self.tests_failed == 0 else 1

def main():
    """Main test runner"""
    
    # Test Stock Analytics (Fase 5)
    print("\n" + "="*60)
    print("STOCK ANALYTICS (FASE 5) - BACKEND API TESTS")
    print("="*60)
    
    sa_tester = StockAnalyticsAPITester()
    
    # Authentication
    if not sa_tester.test_login():
        print("\n❌ Login failed, stopping Stock Analytics tests")
        return 1
    
    # Stock Analytics Tests
    sa_tester.test_permission_required()
    sa_tester.test_stock_analytics_basic()
    sa_tester.test_warehouse_filter()
    sa_tester.test_category_filter()
    sa_tester.test_classification_logic()
    sa_tester.test_sold_qty_window()
    
    # Print Stock Analytics summary
    sa_result = sa_tester.print_summary()
    
    # Test Financial Statements (existing tests)
    print("\n" + "="*60)
    print("FINANCIAL STATEMENTS MODULE - BACKEND API TESTS")
    print("="*60)
    
    tester = FinancialStatementsAPITester()
    
    # Authentication
    if not tester.test_login():
        print("\n❌ Login failed, stopping Financial tests")
        return 1
    
    # Income Statement Tests
    tester.test_income_statement_basic()
    tester.test_income_statement_with_filters()
    
    # Balance Sheet Tests
    tester.test_balance_sheet_single()
    tester.test_balance_sheet_comparative()
    
    # CSV Export Tests
    tester.test_income_statement_csv_export()
    tester.test_balance_sheet_csv_export_single()
    tester.test_balance_sheet_csv_export_comparative()
    
    # Entity Scoping Tests
    tester.test_entity_scoping_param()
    tester.test_entity_scoping_header()
    
    # GL Regression Tests
    tester.test_gl_regression_trial_balance()
    tester.test_gl_regression_summary()
    tester.test_gl_regression_journal()
    
    # Print Financial summary
    fin_result = tester.print_summary()
    
    # Return combined result
    return max(sa_result, fin_result)

if __name__ == "__main__":
    sys.exit(main())
