"""The one step the model is allowed to take.

It reads the question and names panels. That is all. It does not see a
row, it does not see a figure, and it does not do arithmetic.

Every test here hands in a fake model, so nothing reaches the network and
nothing needs a key. The board is the cost view's; the anomaly view uses
the same function with its own.
"""

import json

import cost_panels
import routing

BOARD = cost_panels.BOARD


def plan(*names, reason='because'):
    """What a well behaved model replies with."""
    return json.dumps({'panels': list(names), 'reason': reason})


def route(question, model, **extra):
    return routing.route(question, model=model, board=BOARD, **extra)


class TestItAsksTheModelOnce:
    def test_one_question_is_one_call(self, fake_model):
        model = fake_model(plan('landed'))

        route('what did it cost?', model)

        assert len(model.calls) == 1

    def test_the_question_is_in_the_prompt(self, fake_model):
        model = fake_model(plan('landed'))

        route('what did it cost?', model)

        assert 'what did it cost?' in model.calls[0]

    def test_the_menu_is_in_the_prompt(self, fake_model):
        """The model chooses from a list it was shown. Without the list
        it would guess, and a guess is an invented panel."""
        model = fake_model(plan('landed'))

        route('what did it cost?', model)

        for name in ('landed', 'by_component', 'by_carrier', 'by_month'):
            assert name in model.calls[0]

    def test_the_word_json_is_in_the_prompt(self, fake_model):
        """DeepSeek refuses JSON mode unless the prompt says json."""
        model = fake_model(plan('landed'))

        route('what did it cost?', model)

        assert 'json' in model.calls[0].lower()

    def test_no_line_is_in_the_prompt(self, fake_model, lines):
        """Sending the data would let the model answer from it, and then
        the figure would be its opinion rather than a calculation."""
        model = fake_model(plan('landed'))

        route('what did it cost?', model)

        assert 'B/L MRK7000001' not in model.calls[0]
        assert '24659' not in model.calls[0]


class TestWhatComesBack:
    def test_the_plan_names_panels(self, fake_model):
        model = fake_model(plan('landed', 'by_component'))

        routed = route('what did it cost?', model)

        assert routed.panels[:2] == ['landed', 'by_component']

    def test_the_plan_keeps_the_question(self, fake_model):
        routed = route('what did it cost?', fake_model(plan('landed')))

        assert routed.question == 'what did it cost?'

    def test_a_panel_the_model_invented_is_dropped(self, fake_model):
        model = fake_model(plan('landed', 'by_cost_centre'))

        routed = route('what did it cost?', model)

        assert routed.panels[0] == 'landed'
        assert 'by_cost_centre' not in routed.panels

    def test_a_dropped_panel_is_recorded_not_hidden(self, fake_model):
        model = fake_model(plan('landed', 'by_cost_centre'))

        assert route('what did it cost?', model).ignored == ['by_cost_centre']

    def test_the_same_panel_twice_is_opened_once(self, fake_model):
        model = fake_model(plan('landed', 'landed'))

        assert route('what did it cost?', model).panels.count('landed') == 1

    def test_the_order_the_model_gave_is_kept(self, fake_model):
        model = fake_model(plan('by_month', 'landed', 'by_carrier'))

        routed = route('what did it cost?', model)

        assert routed.panels[:3] == ['by_month', 'landed', 'by_carrier']


class TestSomebodyWhoDoesNotKnowTheNames:
    """A reader asks about "the yellow line" and "the ring", because that
    is what is in front of them."""

    def test_the_prompt_describes_what_each_panel_looks_like(self,
                                                             fake_model):
        model = fake_model(plan('landed'))

        route('what is the yellow line?', model)

        said = model.calls[0].lower()
        assert 'yellow' in said
        assert 'ring' in said


class TestAnAnswerIsSeveralPanels:
    def test_the_prompt_asks_for_three_to_five(self, fake_model):
        model = fake_model(plan('landed'))

        route('what did it cost?', model)

        assert 'three' in model.calls[0] and 'five' in model.calls[0]

    def test_one_panel_is_topped_up_to_three(self, fake_model):
        routed = route('who moved it?', fake_model(plan('by_carrier')))

        assert len(routed.panels) >= 3
        assert routed.panels[0] == 'by_carrier'

    def test_more_than_five_is_cut_to_five(self, fake_model):
        model = fake_model(plan(*cost_panels.MENU))

        assert len(route('everything', model).panels) == 5

    def test_every_panel_added_is_on_the_menu(self, fake_model):
        routed = route('which shipment?', fake_model(plan('by_shipment')))

        for name in routed.panels:
            assert name in cost_panels.MENU

    def test_nothing_is_added_twice(self, fake_model):
        routed = route('what did it cost?',
                       fake_model(plan('landed', 'by_component')))

        assert len(set(routed.panels)) == len(routed.panels)

    def test_a_refusal_is_not_topped_up(self, fake_model):
        """Three panels nobody asked for is worse than an honest no."""
        model = fake_model('not json', 'still not json')

        assert route('what did it cost?', model).panels == []


class TestSomethingThatIsNotAQuestion:
    def test_a_greeting_is_not_an_error(self, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}))

        routed = route('hi', model)

        assert routed.small_talk
        assert not routed.refusal

    def test_the_greeting_costs_one_call_and_no_more(self, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}))

        route('hi', model)

        assert len(model.calls) == 1

    def test_the_prompt_tells_the_model_this_is_allowed(self, fake_model):
        model = fake_model(plan('landed'))

        route('hi', model)

        assert 'small_talk' in model.calls[0]


class TestItTriesAgainBeforeGivingUp:
    def test_prose_gets_one_repair_attempt(self, fake_model):
        model = fake_model('Sure! Here is your cost.', plan('landed'))

        routed = route('what did it cost?', model)

        assert routed.panels[0] == 'landed'
        assert len(model.calls) == 2

    def test_the_repair_shows_the_model_what_it_said(self, fake_model):
        model = fake_model('Sure!', plan('landed'))

        route('what did it cost?', model)

        assert 'Sure!' in model.calls[1]

    def test_two_failures_is_a_refusal(self, fake_model):
        """One retry, not a loop. Every attempt costs a second."""
        model = fake_model('Sure!', 'Still not json.')

        routed = route('what did it cost?', model)

        assert routed.refusal
        assert len(model.calls) == 2


class TestWhenTheModelMisbehaves:
    def test_json_with_no_panels_is_a_refusal(self, fake_model):
        model = fake_model(json.dumps({'reason': 'I do not know'}))

        routed = route('what did it cost?', model)

        assert routed.refusal
        assert 'landed cost' in routed.refusal

    def test_every_panel_invented_is_a_refusal(self, fake_model):
        model = fake_model(plan('by_branch', 'by_cost_centre', 'by_payer'))

        routed = route('what did it cost?', model)

        assert routed.refusal
        assert routed.panels == []

    def test_a_model_that_raises_is_a_refusal_not_a_crash(self):
        def broken(prompt):
            raise ConnectionError('deepseek is unreachable')

        routed = route('what did it cost?', broken)

        assert 'unreachable' in routed.refusal


class TestTheModelNeverComputes:
    def test_a_figure_in_the_reply_is_thrown_away(self, fake_model):
        """Even a correct figure is thrown away."""
        model = fake_model(json.dumps({
            'panels': ['landed'],
            'landed_total': '24659.00',
            'answer': 'It cost 24,659.00.',
        }))

        routed = route('what did it cost?', model)

        assert not hasattr(routed, 'landed_total')
        assert routed.panels[0] == 'landed'

    def test_routing_does_not_import_the_figures(self):
        """If this module could compute, one day it would."""
        with open(routing.__file__, encoding='utf-8') as text:
            body = text.read()

        for module in ('cost', 'anomalies'):
            assert f'import {module}' not in body
            assert f'from {module}' not in body
