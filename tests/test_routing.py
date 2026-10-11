"""The one step the model is allowed to take.

It reads the question and names panels. That is all. It does not see a
row, it does not see a figure, and it does not do arithmetic.

Every test here hands in a fake model, so nothing reaches the network and
nothing needs a key. The real model is passed the same way, which is the
point of passing it at all.
"""

import json

import routing


def plan(*names, reason='because'):
    """What a well behaved model replies with."""
    return json.dumps({'panels': list(names), 'reason': reason})


class TestItAsksTheModelOnce:
    def test_one_question_is_one_call(self, fake_model):
        model = fake_model(plan('overdue'))

        routing.route('how much is late?', model=model)

        assert len(model.calls) == 1

    def test_the_question_is_in_the_prompt(self, fake_model):
        model = fake_model(plan('overdue'))

        routing.route('how much is late?', model=model)

        assert 'how much is late?' in model.calls[0]

    def test_the_menu_is_in_the_prompt(self, fake_model):
        """The model chooses from a list it was shown. Without the list
        it would guess, and a guess is an invented panel."""
        model = fake_model(plan('overdue'))

        routing.route('how much is late?', model=model)

        for name in ('balance', 'overdue', 'by_supplier', 'by_month'):
            assert name in model.calls[0]

    def test_the_word_json_is_in_the_prompt(self, fake_model):
        """DeepSeek refuses JSON mode unless the prompt says json. This
        is their rule, not ours, and forgetting it fails at runtime."""
        model = fake_model(plan('overdue'))

        routing.route('how much is late?', model=model)

        assert 'json' in model.calls[0].lower()

    def test_no_rows_are_in_the_prompt(self, fake_model, owed):
        """Sending the data would let the model answer from it, and then
        the figure would be its opinion rather than a calculation."""
        model = fake_model(plan('overdue'))

        routing.route('how much is late?', model=model, owed=owed)

        assert 'NCL-2026-3001' not in model.calls[0]
        assert '67450' not in model.calls[0]


class TestWhatComesBack:
    def test_the_plan_names_panels(self, fake_model):
        model = fake_model(plan('overdue', 'by_band'))

        routed = routing.route('how much is late?', model=model)

        assert routed.panels[:2] == ['overdue', 'by_band']

    def test_the_plan_keeps_the_question(self, fake_model):
        model = fake_model(plan('overdue'))

        routed = routing.route('how much is late?', model=model)

        assert routed.question == 'how much is late?'

    def test_a_panel_the_model_invented_is_dropped(self, fake_model):
        """The menu is the gate. A model that asks for `by_cost_centre`
        gets the panels that do exist and nothing else."""
        model = fake_model(plan('overdue', 'by_cost_centre'))

        routed = routing.route('how much is late?', model=model)

        assert routed.panels[0] == 'overdue'
        assert 'by_cost_centre' not in routed.panels

    def test_a_dropped_panel_is_recorded_not_hidden(self, fake_model):
        model = fake_model(plan('overdue', 'by_cost_centre'))

        routed = routing.route('how much is late?', model=model)

        assert routed.ignored == ['by_cost_centre']

    def test_the_same_panel_twice_is_opened_once(self, fake_model):
        model = fake_model(plan('overdue', 'overdue'))

        routed = routing.route('how much is late?', model=model)

        assert routed.panels.count('overdue') == 1

    def test_the_order_the_model_gave_is_kept(self, fake_model):
        """It read the question. Which panel it put first is the one
        piece of judgement it is trusted with."""
        model = fake_model(plan('by_month', 'overdue', 'by_supplier'))

        routed = routing.route('how much is late?', model=model)

        assert routed.panels[:3] == ['by_month', 'overdue',
                                     'by_supplier']


class TestSomebodyWhoDoesNotKnowTheNames:
    """A reader asks about "the yellow line" and "the ring", because
    that is what is in front of them. Nobody types by_issue_week. The
    model is shown what each panel looks like so it can translate."""

    def test_the_prompt_describes_what_each_panel_looks_like(self,
                                                             fake_model):
        model = fake_model(plan('balance'))

        routing.route('what is the yellow line?', model=model)

        said = model.calls[0].lower()
        assert 'yellow' in said
        assert 'ring' in said or 'donut' in said

    def test_every_panel_on_the_menu_is_described(self):
        import panels as menu

        for name in menu.MENU:
            assert name in routing.LOOKS_LIKE, name

    def test_nothing_is_described_that_is_not_on_the_menu(self):
        import panels as menu

        for name in routing.LOOKS_LIKE:
            assert name in menu.MENU, name


class TestAnAnswerIsSeveralPanels:
    """One panel is a restatement of the sentence. The point of opening
    panels at all is to show the figure from more than one side."""

    def test_the_prompt_asks_for_three_to_five(self, fake_model):
        model = fake_model(plan('balance'))

        routing.route('what do we owe?', model=model)

        assert 'three' in model.calls[0] and 'five' in model.calls[0]

    def test_one_panel_is_topped_up_to_three(self, fake_model):
        model = fake_model(plan('by_supplier'))

        routed = routing.route('who do we owe?', model=model)

        assert len(routed.panels) >= 3

    def test_the_model_s_own_choice_comes_first(self, fake_model):
        """Its judgement about what the question was is the one thing
        it is trusted with, so it is not shuffled."""
        model = fake_model(plan('by_supplier'))

        routed = routing.route('who do we owe?', model=model)

        assert routed.panels[0] == 'by_supplier'

    def test_more_than_five_is_cut_to_five(self, fake_model):
        model = fake_model(plan('balance', 'overdue', 'by_band',
                                'by_supplier', 'by_month', 'by_item',
                                'by_order'))

        routed = routing.route('everything', model=model)

        assert len(routed.panels) == 5

    def test_every_panel_added_is_on_the_menu(self, fake_model):
        import panels as menu
        model = fake_model(plan('by_order'))

        routed = routing.route('which order?', model=model)

        for name in routed.panels:
            assert name in menu.MENU

    def test_nothing_is_added_twice(self, fake_model):
        model = fake_model(plan('balance', 'overdue'))

        routed = routing.route('what do we owe?', model=model)

        assert len(set(routed.panels)) == len(routed.panels)

    def test_a_refusal_is_not_topped_up(self, fake_model):
        """Three panels nobody asked for is worse than an honest no."""
        model = fake_model('not json', 'still not json')

        routed = routing.route('what do we owe?', model=model)

        assert routed.panels == []


class TestSomethingThatIsNotAQuestion:
    def test_a_greeting_is_not_an_error(self, fake_model):
        """Typing hi got back "The model answered without json panels,
        so nothing opened." That is a sentence about the plumbing, and
        no reader should ever see one."""
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}))

        routed = routing.route('hi', model=model)

        assert routed.small_talk
        assert not routed.refusal

    def test_the_greeting_costs_one_call_and_no_more(self, fake_model):
        model = fake_model(json.dumps({'panels': [], 'small_talk': True}))

        routing.route('hi', model=model)

        assert len(model.calls) == 1

    def test_the_prompt_tells_the_model_this_is_allowed(self, fake_model):
        model = fake_model(plan('balance'))

        routing.route('hi', model=model)

        assert 'small_talk' in model.calls[0]


class TestItTriesAgainBeforeGivingUp:
    def test_prose_gets_one_repair_attempt(self, fake_model):
        """A model that forgets the format usually remembers when it is
        shown its own answer and the shape again. Throwing the whole
        turn away on the first slip is wasteful."""
        model = fake_model('Sure! Here are your overdue accounts.',
                           plan('overdue'))

        routed = routing.route('how much is late?', model=model)

        assert routed.panels[0] == 'overdue'
        assert len(model.calls) == 2

    def test_the_repair_shows_the_model_what_it_said(self, fake_model):
        model = fake_model('Sure!', plan('overdue'))

        routing.route('how much is late?', model=model)

        assert 'Sure!' in model.calls[1]

    def test_two_failures_is_a_refusal(self, fake_model):
        """One retry, not a loop. Every attempt costs a second."""
        model = fake_model('Sure!', 'Still not json.')

        routed = routing.route('how much is late?', model=model)

        assert routed.refusal
        assert len(model.calls) == 2


class TestWhenTheModelMisbehaves:
    def test_a_reply_that_is_not_json_is_a_refusal(self, fake_model):
        model = fake_model('Sure! Here are your overdue accounts.')

        routed = routing.route('how much is late?', model=model)

        assert routed.refusal

    def test_json_with_no_panels_is_a_refusal(self, fake_model):
        model = fake_model(json.dumps({'reason': 'I do not know'}))

        routed = routing.route('how much is late?', model=model)

        assert routed.refusal

    def test_every_panel_invented_is_a_refusal(self, fake_model):
        """One bad name out of three is a slip. Three out of three means
        the model did not understand the menu, and opening nothing is
        better than opening the wrong thing."""
        model = fake_model(plan('by_branch', 'by_cost_centre', 'by_payer'))

        routed = routing.route('how much is late?', model=model)

        assert routed.refusal
        assert routed.panels == []

    def test_a_model_that_raises_is_a_refusal_not_a_crash(self):
        """The API goes down. The page has to say so and stay open."""
        def broken(prompt):
            raise ConnectionError('deepseek is unreachable')

        routed = routing.route('how much is late?', model=broken)

        assert routed.refusal
        assert 'unreachable' in routed.refusal or 'reach' in routed.refusal

    def test_a_refusal_opens_no_panels(self, fake_model):
        model = fake_model('not json at all')

        routed = routing.route('how much is late?', model=model)

        assert routed.panels == []


class TestTheModelNeverComputes:
    def test_a_figure_in_the_reply_is_thrown_away(self, fake_model):
        """Even a correct figure is thrown away. Trusting the right
        answer teaches the code to trust the wrong one."""
        model = fake_model(json.dumps({
            'panels': ['overdue'],
            'overdue_total': '31750.00',
            'answer': 'You owe 31,750.00 in overdue invoices.',
        }))

        routed = routing.route('how much is late?', model=model)

        assert not hasattr(routed, 'overdue_total')
        assert routed.panels[0] == 'overdue'

    def test_routing_does_not_import_the_figures(self):
        """If this module could compute, one day it would. Keeping it
        unable is cheaper than keeping it disciplined."""
        source = routing.__file__

        with open(source, encoding='utf-8') as text:
            body = text.read()

        assert 'import metrics' not in body
        assert 'from metrics' not in body
