# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Visual markup for the GL profitability number card and chart."""

from __future__ import unicode_literals

import unittest

from logistics.job_management.profitability_dashboard import (
	_bar_pct,
	render_gl_profitability_dashboard,
)


class TestProfitabilityDashboardMarkup(unittest.TestCase):
	def _sample(self, **overrides):
		data = {
			"currency": "PHP",
			"revenue": 102156,
			"cost": 31804.71,
			"gross_profit": 70351.29,
			"profit_margin_pct": 68.87,
			"wip_amount": 1500,
			"accrual_amount": 250,
			"disbursements_amount": 80,
		}
		data.update(overrides)
		return data

	def test_headline_card_matches_estimated_profitability_design(self):
		html = render_gl_profitability_dashboard(
			self._sample(),
			title="Profitability (from GL)",
			info_title="Figures from General Ledger by Job Number.",
			source_note="Figures from General Ledger by Job Number.",
		)
		self.assertIn("lg-profit-card", html)
		self.assertIn("border:1px solid #198754", html)
		self.assertIn("Profitability (from GL)", html)
		self.assertIn("Total Revenue", html)
		self.assertIn("Total Cost", html)
		self.assertIn("Gross Profit", html)
		self.assertIn("Margin %", html)
		self.assertIn("68.87%", html)
		self.assertIn("(Excl. Tax)", html)
		self.assertIn("(Profit ÷ Revenue)", html)
		self.assertIn("color:#198754", html)
		self.assertIn("color:#212529", html)
		self.assertIn("102,156.00", html)
		self.assertIn("31,804.71", html)
		self.assertIn("lg-profit-metrics-4", html)
		self.assertIn("@media (max-width: 480px)", html)
		self.assertIn("lg-profit-supporting", html)
		self.assertIn("WIP Amount", html)
		self.assertIn("Accrual Amount", html)
		self.assertIn("Disbursements", html)

	def test_chart_uses_the_same_card_and_scales_bars(self):
		html = render_gl_profitability_dashboard(
			self._sample(),
			title="Profitability (from GL)",
			info_title="source",
			source_note="source",
		)
		self.assertIn("Revenue vs Cost", html)
		self.assertIn("fa-bar-chart", html)
		cost_pct = _bar_pct(31804.71, 102156)
		self.assertEqual(cost_pct, 31.13)
		self.assertIn("width:{0}%".format(cost_pct), html)
		self.assertIn("width:100.0%", html)

	def test_negative_profit_and_margin_use_red(self):
		html = render_gl_profitability_dashboard(
			self._sample(revenue=100, cost=250, gross_profit=-150, profit_margin_pct=-150),
			title="Profitability (from GL)",
			info_title="source",
			source_note="source",
		)
		self.assertIn("color:#dc3545", html)
		self.assertIn("-150.00%", html)

	def test_empty_banner_and_header_extra_are_kept(self):
		html = render_gl_profitability_dashboard(
			self._sample(revenue=0, cost=0, gross_profit=0, profit_margin_pct=0),
			title="Project Profitability (from GL)",
			info_title="Aggregated from General Ledger.",
			source_note="Aggregated from General Ledger.",
			header_extra_html='<a href="/app/project/PRJ">PRJ</a>',
			empty_banner_html='<div class="logistics-profitability-empty-state">Empty</div>',
		)
		self.assertIn("logistics-profitability-empty-state", html)
		self.assertIn('href="/app/project/PRJ"', html)
		self.assertIn("Project Profitability (from GL)", html)
		self.assertIn("Aggregated from General Ledger.", html)
