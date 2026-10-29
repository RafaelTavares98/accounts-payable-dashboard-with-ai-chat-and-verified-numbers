"""The steps of the video, in order, on the cost view.

Nothing new is built here. Every part already has its own file. This is
the file that fails when the parts are each correct and do not join up,
which is the failure the other files cannot see.

The steps are the ones written down in `docs/reference-behavior.md`.
"""

import json
from decimal import Decimal

import cost
import cost_answering
import cost_panels

D = Decimal


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


class TestStepOneTheDashboardOpens:
    def test_it_opens_on_the_report_project_01_writes(self, fixtures):
        """Not on figures built for the occasion. On the files the other
        project writes, in the same columns."""
        lines = cost.load(fixtures / 'cost')

        opening = cost_panels.build('landed', lines)

        assert dict(opening.rows)['Landed cost'] == D('24659.00')

    def test_the_filters_are_offered_from_the_data_itself(self, lines):
        assert len(cost.choices(lines)['carrier']) == 3


class TestStepThreeAChipIsClicked:
    def test_a_click_opens_panels_with_no_model_and_no_key(self, lines,
                                                           today):
        answer = cost_answering.click(cost_answering.CHIPS[0], lines,
                                      today=today)

        assert answer.panels
        assert answer.sentence


class TestStepSixThePanelsOpen:
    def test_one_question_opens_several_panels(self, lines, today,
                                               fake_model):
        model = fake_model(plan('landed', 'by_component', 'by_carrier',
                                'by_month'), 'Some words.')

        answer = cost_answering.answer('what did it cost?', lines,
                                       today=today, model=model)

        assert len(answer.panels) == 4

    def test_the_panels_agree_with_each_other(self, lines, today,
                                              fake_model):
        """The carrier bars, the parts ring and the month line are three
        pictures of one total. They add to the same number."""
        model = fake_model(plan('by_carrier', 'by_component', 'by_month'),
                           'Some words.')

        answer = cost_answering.answer('what did it cost?', lines,
                                       today=today, model=model)
        totals = {sum(value for _, value in panel.rows)
                  for panel in answer.panels}

        assert totals == {D('24659.00')}


class TestStepSevenTheCycleRepeats:
    def test_a_different_question_opens_a_different_set(self, lines, today,
                                                        fake_model):
        model = fake_model(plan('landed', 'by_month'), 'Some words.',
                           plan('by_carrier', 'by_mode'), 'Other words.')

        first = cost_answering.answer('what did it cost?', lines,
                                      today=today, model=model)
        second = cost_answering.answer('who moved it?', lines,
                                       today=today, model=model)

        assert [p.name for p in first.panels] != \
            [p.name for p in second.panels]


class TestTheOneRule:
    def test_a_lying_model_changes_nothing_on_the_page(self, lines, today,
                                                       fake_model):
        model = fake_model(plan('landed'),
                           'It cost 1,000,000.00, since 1999.')

        answer = cost_answering.answer('what did it cost?', lines,
                                       today=today, model=model)

        assert '1,000,000.00' not in answer.sentence
        assert dict(answer.panels[0].rows)['Landed cost'] == D('24659.00')
