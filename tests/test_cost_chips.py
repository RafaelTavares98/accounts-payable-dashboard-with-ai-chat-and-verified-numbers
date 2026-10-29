"""The ready-made questions on the cost view.

A chip is not a question for the model. It already knows which panels it
opens, so it works with no API key and no network. The model is only
needed when somebody types something nobody wrote down.
"""

import cost
import cost_answering
import cost_panels

CHIPS = cost_answering.CHIPS


class TestTheChips:
    def test_there_are_five_of_them(self):
        assert len(CHIPS) == 5

    def test_each_one_is_a_question_a_person_would_ask(self):
        for chip in CHIPS:
            assert chip.question.endswith('?')

    def test_they_ask_cost_questions(self):
        asked = ' '.join(chip.question.lower() for chip in CHIPS)

        for subject in ('cost', 'carrier', 'part', 'provisional'):
            assert subject in asked

    def test_every_panel_a_chip_names_is_on_the_menu(self):
        for chip in CHIPS:
            for name in chip.panels:
                assert name in cost_panels.MENU, f'{chip.question} wants {name}'

    def test_a_chip_opens_three_to_five_panels(self, lines, today):
        for chip in CHIPS:
            answer = cost_answering.click(chip, lines, today=today)

            assert 3 <= len(answer.panels) <= 5, chip.question

    def test_the_chip_s_own_panels_come_first(self, lines, today):
        chip = CHIPS[2]

        answer = cost_answering.click(chip, lines, today=today)

        assert answer.panels[0].name == chip.panels[0]


class TestClickingOne:
    def test_a_chip_needs_no_model(self, lines, today):
        assert cost_answering.click(CHIPS[0], lines, today=today).panels

    def test_the_sentence_carries_a_real_figure(self, lines, today):
        answer = cost_answering.click(CHIPS[0], lines, today=today)

        assert '24,659.00' in answer.sentence
        assert '1,100.00' in answer.sentence

    def test_the_unit_cost_keeps_its_four_places(self, lines, today):
        """A cap that lands at 0.4577 a unit is not 0.46 a unit to a cost
        team multiplying it by a hundred thousand."""
        answer = cost_answering.click(CHIPS[3], lines, today=today)

        assert '11.1770 a unit' in answer.sentence

    def test_every_chip_answers_without_refusing(self, lines, today):
        for chip in CHIPS:
            assert not cost_answering.click(chip, lines, today=today).refusal

    def test_a_chip_clicked_twice_gives_the_same_answer(self, lines, today):
        first = cost_answering.click(CHIPS[1], lines, today=today)
        second = cost_answering.click(CHIPS[1], lines, today=today)

        assert first.sentence == second.sentence


class TestAChipRespectsTheFilters:
    def test_it_answers_over_what_is_on_screen(self, lines, today):
        air = cost.only(lines, mode='air')

        answer = cost_answering.click(CHIPS[0], air, today=today)

        assert '7,074.50' in answer.sentence

    def test_a_chip_over_an_empty_filter_refuses(self, today):
        assert cost_answering.click(CHIPS[0], [], today=today).refusal
