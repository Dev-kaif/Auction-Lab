from decimal import Decimal as D

import numpy as np
import pytest

from app.auctions.engine import run_auction
from app.auctions.models import AuctionInputError, Mechanism
from app.simulation.engine import run_batch


VALUES = [100, 80, 60, 40]
BIDS = [100, 80, 60, 40]
CTRS = [1.0, 0.7, 0.4]


def test_gsp_assigns_slots_and_charges_next_bid_per_click():
    result = run_auction(VALUES, BIDS, Mechanism.GSP, CTRS)
    rows = {row.advertiser: row for row in result.results}
    assert [rows[name].slot for name in "ABCD"] == [1, 2, 3, None]
    assert [rows[name].payment_per_click for name in "ABC"] == [D("80.00"), D("60.00"), D("40.00")]
    assert [rows[name].expected_payment for name in "ABC"] == [D("80.00"), D("42.00"), D("16.00")]
    assert [rows[name].expected_utility for name in "ABC"] == [D("20.00"), D("14.00"), D("8.00")]
    assert result.revenue == D("138.00")
    assert result.social_welfare == D("180.00")


def test_vcg_externality_payments_and_truthful_welfare():
    result = run_auction(VALUES, BIDS, Mechanism.VCG, CTRS)
    rows = {row.advertiser: row for row in result.results}
    assert [rows[name].expected_payment for name in "ABCD"] == [D("58.00"), D("34.00"), D("16.00"), D("0.00")]
    assert [rows[name].expected_utility for name in "ABCD"] == [D("42.00"), D("22.00"), D("8.00"), D("0.00")]
    assert result.revenue == D("108.00")
    assert result.social_welfare == D("180.00")
    assert rows["B"].payment_per_click == D("48.57")


@pytest.mark.parametrize("rates", [[], [1, .8, .9], [1, -0.1], [1, 1.01], [1, float("nan")], [1, .5, .3, .1, 0]])
def test_invalid_slot_ctr_rates_are_rejected(rates):
    with pytest.raises(AuctionInputError):
        run_auction(VALUES, BIDS, Mechanism.GSP, rates)


def test_gsp_ties_follow_advertiser_priority_and_fourth_slot_has_no_next_bid():
    result = run_auction(VALUES, [50, 50, 30, 10], Mechanism.GSP, [1, .7, .4, .2])
    rows = {row.advertiser: row for row in result.results}
    assert [result.results[index].slot for index in range(4)] == [1, 2, 3, 4]
    assert rows["C"].payment_per_click == D("10.00")
    assert rows["D"].payment_per_click == D("0.00")


@pytest.mark.parametrize("mechanism", [Mechanism.GSP, Mechanism.VCG])
def test_vectorized_multi_slot_matches_exact_engine(mechanism):
    valuations = np.array([VALUES, [20, 50, 50, 10], [0, 0, 0, 0]], dtype=float)
    bids = np.array([BIDS, [50, 50, 30, 10], [0, 0, 0, 0]], dtype=float)
    batch = run_batch(valuations, bids, mechanism, CTRS)
    for i in range(len(valuations)):
        exact = run_auction(valuations[i], bids[i], mechanism, CTRS)
        assert batch.slot_assignment[i].tolist() == [row.slot or -1 for row in exact.results]
        assert batch.revenue[i] == pytest.approx(float(exact.revenue))
        assert batch.payoffs[i].tolist() == pytest.approx([float(row.expected_utility) for row in exact.results])


def test_gsp_simulation_aggregates_expose_expected_metrics():
    valuations = np.tile(np.array(VALUES, dtype=float), (3, 1))
    batch = run_batch(valuations, valuations, Mechanism.GSP, CTRS)
    assert batch.revenue.tolist() == pytest.approx([138.0] * 3)
    assert batch.social_welfare.tolist() == pytest.approx([180.0] * 3)
