"""The ready-made questions in the chat.

In the video the user never types. He clicks a chip and the panels open.
That is what makes the demo repeatable, and it is what makes it work with
no API key and no network.

So a chip is not a question for the model. A chip already knows which
panels it opens. The model is only needed when somebody types something
nobody wrote down.
"""

import suggestions


class TestTheChips:
    def test_there_are_five_of_them(self):
        """The video shows five. More than that and the chat panel reads
        as a menu rather than a hint."""
        assert len(suggestions.CHIPS) == 5

    def test_each_one_is_a_question_a_person_would_ask(self):
        for chip in suggestions.CHIPS:
            assert chip.question.endswith('?')

    def test_they_cover_the_five_the_reference_shows(self):
        asked = ' '.join(chip.question.lower() for chip in suggestions.CHIPS)

        for subject in ('total', 'open', 'supplier', 'overdue', 'late'):
            assert subject in asked

    def test_each_one_names_the_panels_it_opens(self):
        for chip in suggestions.CHIPS:
            assert chip.panels

    def test_a_chip_opens_three_to_five_panels(self, owed, today):
        """A chip that opens one panel shows the sentence again in a
        box. The typed questions already open three to five; a chip is
        the same question with the typing done for you."""
        for chip in suggestions.CHIPS:
            answer = suggestions.click(chip, owed, today=today)

            assert 3 <= len(answer.panels) <= 5, chip.question

    def test_the_chip_s_own_panels_come_first(self, owed, today):
        chip = suggestions.CHIPS[2]

        answer = suggestions.click(chip, owed, today=today)

        assert [p.name for p in answer.panels][:len(chip.panels)] == \
            chip.panels

    def test_every_panel_a_chip_names_is_on_the_menu(self):
        import panels

        for chip in suggestions.CHIPS:
            for name in chip.panels:
                assert name in panels.MENU, f'{chip.question} wants {name}'


class TestClickingOne:
    def test_a_chip_needs_no_model(self, owed, today):
        """No key, no network, no cost, no wait. The first thing anybody
        clicks must work on a train."""
        answer = suggestions.click(suggestions.CHIPS[0], owed, today=today)

        assert answer.panels

    def test_a_chip_makes_no_model_call(self, owed, today, fake_model):
        model = fake_model()

        suggestions.click(suggestions.CHIPS[0], owed, today=today,
                          model=model)

        assert model.calls == []

    def test_its_sentence_is_written_by_code(self, owed, today):
        answer = suggestions.click(suggestions.CHIPS[0], owed, today=today)

        assert answer.sentence

    def test_the_sentence_carries_a_real_figure(self, owed, today):
        total = suggestions.click(suggestions.CHIPS[0], owed, today=today)

        assert '67,450.00' in total.sentence

    def test_every_chip_answers_without_refusing(self, owed, today):
        """A chip that refuses on the demo data is a chip that should
        not be on the panel."""
        for chip in suggestions.CHIPS:
            answer = suggestions.click(chip, owed, today=today)

            assert not answer.refusal, chip.question

    def test_a_chip_clicked_twice_gives_the_same_answer(self, owed, today):
        first = suggestions.click(suggestions.CHIPS[0], owed, today=today)
        second = suggestions.click(suggestions.CHIPS[0], owed, today=today)

        assert first.sentence == second.sentence


class TestAChipRespectsTheFilters:
    def test_it_answers_over_what_is_on_screen(self, owed, today):
        import filtering
        marsk = filtering.apply(owed, supplier='Marsk Line Agencies B.V.')

        answer = suggestions.click(suggestions.CHIPS[0], marsk, today=today)

        assert '5,500.00' in answer.sentence

    def test_a_chip_over_an_empty_filter_refuses(self, today):
        answer = suggestions.click(suggestions.CHIPS[0], [], today=today)

        assert answer.refusal
