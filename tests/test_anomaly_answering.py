"""The assistant on the anomaly view.

It works like the one beside the cost view: the model names panels off a
fixed menu, code computes every figure, the model writes one sentence,
and a sentence carrying a number nobody computed is thrown away. The menu
is the anomaly menu; a cost panel is not on it.
"""

import json

import pytest

import anomalies
import anomaly_answering
import anomaly_panels
import routing


@pytest.fixture
def scored(fixtures):
    return anomalies.load(fixtures)


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


class TestTheMenu:
    def test_every_panel_builds(self, scored):
        for name in anomaly_panels.MENU:
            built = anomaly_panels.build(name, scored)
            assert built.rows

    def test_the_flags_panel_holds_the_headline(self, scored):
        built = anomaly_panels.build('flags', scored)

        assert dict(built.rows)['Flagged'] == 4

    def test_no_name_is_shared_with_the_cost_menu(self):
        import cost_panels
        assert not set(anomaly_panels.MENU) & set(cost_panels.MENU)

    def test_an_unknown_panel_is_refused(self, scored):
        with pytest.raises(anomaly_panels.NoSuchPanel):
            anomaly_panels.build('by_carrier', scored)

    def test_the_origin_panel_puts_ours_beside_the_client_s(self, scored):
        built = anomaly_panels.build('by_origin', scored, ours=1)

        assert dict(built.rows) == {
            'Our errors, read by a person': 1,
            'Client errors, confirmed': 2,
            'Client, waiting for the analyst': 1,
            'Dismissed, invoice was right': 1,
        }


class TestRouting:
    def test_the_prompt_offers_the_anomaly_menu_only(self, fake_model):
        model = fake_model(plan('flags'))
        routing.route('what was flagged?', model, board=anomaly_panels.BOARD)

        assert 'by_stage' in model.calls[0]
        assert 'by_carrier' not in model.calls[0]

    def test_a_cost_panel_is_not_opened(self, fake_model):
        routed = routing.route('x', fake_model(plan('by_carrier')),
                               board=anomaly_panels.BOARD)

        assert routed.panels == []
        assert routed.refusal


class TestAnswering:
    def test_a_question_opens_one_panel(self, scored, fake_model):
        model = fake_model(plan('by_stage'), 'Freight billing holds the most flags.')
        answer = anomaly_answering.answer('where do errors happen?', scored,
                                          model=model)

        assert answer.panels[0].name == 'by_stage'
        assert len(answer.panels) == 1
        assert answer.sentence == 'Freight billing holds the most flags.'
        assert not answer.rejected

    def test_a_computed_figure_may_be_quoted(self, scored, fake_model):
        model = fake_model(plan('flags'), '4 invoices were flagged, 8,200.00 in all.')
        answer = anomaly_answering.answer('how many?', scored, model=model)

        assert not answer.rejected

    def test_an_invented_figure_is_thrown_away(self, scored, fake_model):
        model = fake_model(plan('flags'), '17 invoices were flagged.')
        answer = anomaly_answering.answer('how many?', scored, model=model)

        assert answer.rejected
        assert '17' not in answer.sentence
        assert '4' in answer.sentence

    def test_nothing_to_look_at(self, fake_model):
        answer = anomaly_answering.answer('anything?', [], model=fake_model())

        assert answer.refusal

    def test_small_talk_gets_no_panels(self, scored, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}),
                           'Hello. Ask which stage the flags sit in.')
        answer = anomaly_answering.answer('hi', scored, model=model)

        assert answer.panels == []
        assert answer.sentence


class TestChips:
    def test_every_chip_answers_without_a_model(self, scored):
        """A chip always says something. A panel beside it is optional:
        a one-figure answer opens none."""
        for chip in anomaly_answering.CHIPS:
            answer = anomaly_answering.click(chip, scored)
            assert answer.sentence
            assert len(answer.panels) <= 1

    def test_the_first_chip_says_how_many_were_flagged(self, scored):
        answer = anomaly_answering.click(anomaly_answering.CHIPS[0], scored)

        assert answer.sentence.startswith('4 of 8 invoices')

    def test_the_origin_chip_says_whose_errors_they_are(self, scored):
        chip = [c for c in anomaly_answering.CHIPS
                if c.panels == ['by_origin']][0]

        answer = anomaly_answering.click(chip, scored, ours=1)

        assert answer.sentence == ('2 client errors were confirmed and 1 '
                                   'of ours went to a person.')

    def test_a_count_of_ours_may_be_quoted(self, scored, fake_model):
        model = fake_model(plan('by_origin'),
                           'One of ours, 2 confirmed client errors.')

        answer = anomaly_answering.answer('whose?', scored, model=model,
                                          ours=1)

        assert not answer.rejected
