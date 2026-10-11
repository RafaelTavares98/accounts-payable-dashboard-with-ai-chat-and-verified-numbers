"""The seven steps of the video, in order, as one test each.

Nothing new is built here. Every part already has its own file. This is
the file that fails when the parts are each correct and do not join up,
which is the failure the other files cannot see.

The steps are the ones written down in
`docs/reference-behavior.md`, numbered the same way.
"""

import json
from decimal import Decimal

import answering
import filtering
import panels
import payables
import suggestions


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


class TestStepOneTheDashboardOpens:
    def test_it_opens_on_the_real_csv(self, fixtures, today):
        """Not on a fixture built for the occasion. On the file the
        other project writes."""
        rows = payables.payable(payables.load(fixtures))

        opening = panels.build('balance', rows, today=today)

        assert dict(opening.rows)['Total owed'] == Decimal('67450.00')

    def test_it_opens_before_anybody_touches_the_model(self, owed, today):
        assert panels.build('overdue', owed, today=today).rows

    def test_the_filters_are_offered_from_the_data_itself(self, owed):
        """Nobody types the supplier list into the page. It is whatever
        the file holds."""
        assert len(filtering.suppliers(owed)) == 5


class TestStepThreeAChipIsClicked:
    def test_a_click_opens_panels_with_no_model_and_no_key(self, owed,
                                                           today):
        answer = suggestions.click(suggestions.CHIPS[0], owed, today=today)

        assert answer.panels
        assert answer.sentence


class TestStepFourTheAnswerArrives:
    def test_the_sentence_names_the_figure_and_the_slice(self, owed, today,
                                                         fake_model):
        """The video's own example: "3.483 contas vencidas no filtro
        atual do painel, com atraso médio de 482 dias." Two figures and
        a statement of which rows they came from."""
        model = fake_model(plan('overdue'),
                           '4 documents are overdue in the current filter, '
                           'an average of 31.5 days late.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert not answer.rejected
        assert answer.rows_used == 10


class TestStepSixThePanelsOpen:
    def test_one_question_opens_several_panels(self, owed, today,
                                               fake_model):
        """The same analysis through another dimension: by month, by
        supplier, by band."""
        model = fake_model(plan('overdue', 'by_band', 'by_supplier',
                                'by_month'),
                           '31,750.00 is overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert len(answer.panels) == 4

    def test_every_panel_is_computed_over_the_same_rows(self, owed, today,
                                                        fake_model):
        """They are views of one thing. If two panels disagree about how
        many rows they covered, they are two answers wearing one."""
        model = fake_model(plan('overdue', 'by_supplier'), 'Some words.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert {figure.rows for figure in answer.figures} == {10}

    def test_the_panels_agree_with_each_other(self, owed, today,
                                              fake_model):
        """The supplier bars and the month line are two pictures of one
        total. They have to add to the same number."""
        model = fake_model(plan('by_supplier', 'by_month'), 'Some words.')

        answer = answering.answer('what do we owe?', owed,
                                  today=today, model=model)
        by_supplier, by_month = answer.panels[:2]

        assert sum(value for _, value in by_supplier.rows) == \
            sum(value for _, value in by_month.rows)


class TestStepSevenTheCycleRepeats:
    def test_a_second_question_replaces_the_panels(self, owed, today,
                                                   fake_model):
        model = fake_model(plan('overdue'), 'Some words.',
                           plan('by_supplier'), 'Other words.')

        first = answering.answer('how much is late?', owed,
                                 today=today, model=model)
        second = answering.answer('who do we owe?', owed,
                                  today=today, model=model)

        assert first.panels[0].name == 'overdue'
        assert second.panels[0].name == 'by_supplier'

    def test_a_different_question_opens_a_different_set(self, owed, today,
                                                        fake_model):
        """This is the behaviour the video is actually selling. If every
        question opened the same panels, the model would be decoration."""
        model = fake_model(plan('overdue', 'by_band'), 'Some words.',
                           plan('by_supplier', 'by_item'), 'Other words.')

        late = answering.answer('how much is late?', owed,
                                today=today, model=model)
        who = answering.answer('who do we owe the most to?', owed,
                               today=today, model=model)

        assert [p.name for p in late.panels] != [p.name for p in who.panels]

    def test_each_answer_keeps_its_own_panels(self, owed, today,
                                              fake_model):
        """The chat scrolls, and an old answer can be reopened. It has
        to still carry what it showed, not recompute it."""
        model = fake_model(plan('overdue'), 'Some words.',
                           plan('by_supplier'), 'Other words.')

        first = answering.answer('how much is late?', owed,
                                 today=today, model=model)
        answering.answer('who do we owe?', owed, today=today, model=model)

        assert dict(first.panels[0].rows)['Overdue'] == Decimal('31750.00')


class TestTheOneRule:
    def test_the_model_produced_no_figure_anywhere(self, owed, today,
                                                   fake_model):
        """The whole project in one assertion. Every number in the
        answer came back out of a function, over a stated number of
        rows."""
        import metrics
        model = fake_model(plan('overdue', 'by_supplier', 'by_month'),
                           '31,750.00 is overdue.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        for figure in answer.figures:
            assert figure.name in metrics.FIGURES
            assert figure.value == metrics.compute(figure.name, owed,
                                                   today=today)

    def test_a_lying_model_changes_nothing_on_the_page(self, owed, today,
                                                       fake_model):
        model = fake_model(plan('overdue'),
                           'You owe 1,000,000.00, overdue since 1999.')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=model)

        assert '1,000,000.00' not in answer.sentence
        assert dict(answer.panels[0].rows)['Overdue'] == Decimal('31750.00')
