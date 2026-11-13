"""Regression checks: no network, screen capture, or keyboard events."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import monitor


class MonitorTests(unittest.TestCase):
    def test_invalid_answers_cannot_flash(self):
        for value in ([], None, 42, True, {},
                      {"answer": "", "found": True},
                      {"answer": "AB", "found": True},
                      {"answer": "A", "found": "false"}):
            with self.subTest(value=value):
                self.assertEqual(monitor.parse_answer(json.dumps(value)), 0)

    def test_env_is_relative_to_script_and_accepts_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, '.env').write_text('MONITOR_TEST_KEY=value\n', encoding='utf-8-sig')
            with patch.object(monitor, '__file__', str(Path(folder, 'monitor.py'))), \
                    patch.dict(os.environ, {}, clear=True):
                monitor.load_env()
                self.assertEqual(os.environ['MONITOR_TEST_KEY'], 'value')
                os.environ['MONITOR_TEST_KEY'] = 'existing'
                monitor.load_env()
                self.assertEqual(os.environ['MONITOR_TEST_KEY'], 'existing')

    def test_capslock_restored_when_interrupted(self):
        with patch.object(monitor.mc, 'caps_lock', return_value=True) as lock, \
                patch.object(monitor.time, 'sleep', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                monitor.flash_n(2)
            self.assertEqual(lock.call_args_list[-1].args, (True,))

    def test_incomplete_response_does_not_use_reasoning_as_answer(self):
        response = {"choices": [{"finish_reason": "length", "message": {
            "content": "", "reasoning_content": '{"answer":"A","found":true}'}}]}
        with patch.object(monitor.urllib.request, 'urlopen',
                          return_value=io.BytesIO(json.dumps(response).encode())):
            with self.assertRaises(ValueError):
                monitor.ask_deepseek(b'png', 'test-key', monitor.DEFAULT_MODEL)

    def test_api_failure_returns_nonzero_and_redacts_key(self):
        error = urllib.error.HTTPError('https://api.deepseek.com', 401, 'Unauthorized', {},
                                       io.BytesIO(b'test-key'))
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), \
                patch.object(monitor.sys, 'argv', ['monitor.py', '--check-api']), \
                patch.object(monitor, 'ask_deepseek', side_effect=error), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(monitor.main(), 1)
            self.assertNotIn('test-key', out.getvalue())
            self.assertIn('[redacted]', out.getvalue())

    def test_malformed_response_returns_nonzero_without_flashing(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), \
                patch.object(monitor.sys, 'argv', ['monitor.py', '--once', '--mute']), \
                patch.object(monitor, 'capture_silent', return_value=(b'png', 'abc', None)), \
                patch.object(monitor, 'ask_deepseek', return_value=('{broken', 'stop')), \
                patch.object(monitor, 'signal_answer') as flash, \
                patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(monitor.main(), 1)
            flash.assert_not_called()

    def test_written_subquestions_save_full_answer_without_flashing(self):
        data = {"found": True, "question_type": "written", "answer": None,
                "question": "a. Jelaskan prinsip. b. Buat sketsa. c. Usulkan perubahan.",
                "response": "a. Perizinan terpadu.\nb. Investor -> Portal -> Kementerian.\nc. Integrasi proses."}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder, 'answer.txt')
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), \
                    patch.object(monitor.sys, 'argv', ['monitor.py', '--once', '--mute', '--answer-file', str(output)]), \
                    patch.object(monitor, 'capture_silent', return_value=(b'png', 'abc', None)), \
                    patch.object(monitor, 'ask_deepseek', return_value=(json.dumps(data), 'stop')), \
                    patch.object(monitor, 'signal_answer') as flash, \
                    patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(monitor.main(), 0)
                flash.assert_not_called()
            saved = output.read_text(encoding='utf-8-sig')
            self.assertIn(data['question'], saved)
            self.assertIn(data['response'], saved)
            self.assertFalse(output.with_name('answer.txt.tmp').exists())

    def test_written_question_cannot_be_treated_as_letter_answer(self):
        text = json.dumps({"found": True, "question_type": "written",
                           "answer": "A", "response": "a. First subquestion"})
        self.assertEqual(monitor.parse_answer(text), 0)
        with self.assertRaises(ValueError):
            monitor.parse_result(text)

    def test_multiple_choice_compatibility_and_missing_question_status(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder, 'answer.txt')
            result = monitor.parse_result('{"found":true,"answer":"B"}')
            monitor.save_result(result, output)
            self.assertIn('ANSWER: B', output.read_text(encoding='utf-8-sig'))
            monitor.save_result(monitor.parse_result('{"found":false,"answer":null}'), output)
            saved = output.read_text(encoding='utf-8-sig')
            self.assertNotIn('ANSWER: B', saved)
            self.assertIn('No readable question detected.', saved)

    def test_all_six_positions_and_unlabeled_options(self):
        for index in range(1, 7):
            with self.subTest(index=index):
                data = {"found": True, "question_type": "multiple_choice",
                        "answer": chr(64 + index), "answer_index": index,
                        "options": ["one", "two", "three", "four", "five", "six"]}
                self.assertEqual(monitor.parse_answer(json.dumps(data)), index)
                data.pop('answer')
                result = monitor.parse_result(json.dumps(data))
                self.assertEqual(result['answer'], chr(64 + index))
                self.assertEqual(result['answer_index'], index)

    def test_invalid_positions_do_not_signal(self):
        for extra in ({"answer": "G"}, {"answer_index": 7},
                      {"answer_index": True}, {"answer_index": 0},
                      {"answer_index": "6"}, {"answer": "A", "answer_index": 6},
                      {"answer": "F", "options": ["one", "two"]}):
            with self.subTest(extra=extra):
                text = json.dumps({"found": True, **extra})
                self.assertEqual(monitor.parse_answer(text), 0)
                with self.assertRaises(ValueError):
                    monitor.parse_result(text)

    def test_exact_beep_count_and_led_restoration(self):
        for count in range(1, 7):
            with self.subTest(count=count), \
                    patch.object(monitor.mc, 'caps_lock', return_value=True) as lock, \
                    patch.object(monitor, 'play_tone') as tone, \
                    patch.object(monitor.time, 'sleep'):
                monitor.signal_answer(count)
                self.assertEqual(tone.call_count, count)
                self.assertTrue(all(call.args == (1000, 180) for call in tone.call_args_list))
                self.assertEqual(lock.call_args_list[-1].args, (True,))

    def test_mute_disables_beeps_and_no_flash_disables_keyboard(self):
        with patch.object(monitor.mc, 'caps_lock') as lock, \
                patch.object(monitor, 'play_tone') as tone, \
                patch.object(monitor.time, 'sleep'):
            monitor.signal_answer(6, use_flash=False, use_sound=False)
            lock.assert_not_called()
            tone.assert_not_called()

    def test_written_completion_and_failure_sound_differ_from_answer(self):
        with patch.object(monitor, 'play_tone') as tone:
            monitor.signal_status('written')
            tone.assert_called_once_with(600, 900)
            tone.reset_mock()
            monitor.signal_status('not_found')
            self.assertEqual([call.args for call in tone.call_args_list], [(250, 450), (180, 600)])

    # --- web grounding ---------------------------------------------------

    def test_search_grounds_answer_when_model_requests_it(self):
        plan = {"found": True, "question_type": "multiple_choice", "answer": "A",
                "answer_index": 1, "options": ["old", "new"],
                "question": "Which was released most recently?",
                "needs_search": True, "search_query": "latest release"}
        grounded = {"found": True, "question_type": "multiple_choice",
                    "answer": "B", "answer_index": 2, "options": ["old", "new"],
                    "question": "Which was released most recently?",
                    "response": "grounded in live results"}
        results = [{"title": "Release notes", "url": "https://example.com/a",
                    "summary": "B shipped later.", "date": "2026-10-01",
                    "authority": 3}]
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web',
                             return_value=results) as search, \
                patch.object(monitor, 'chat',
                             return_value=(json.dumps(grounded), 'stop')) as chat:
            text, finish = monitor.answer_with_search(b'png', 'test-key', 'm')
        self.assertEqual((text, finish), (json.dumps(grounded), 'stop'))
        self.assertEqual(monitor.parse_answer(text), 2)
        search.assert_called_once_with('latest release', 'test-key')
        prompt = chat.call_args.args[2][1]['content']
        self.assertIn('https://example.com/a', prompt)
        self.assertIn('Which was released most recently?', prompt)

    def test_search_is_skipped_when_model_does_not_ask(self):
        plan = {"found": True, "question_type": "multiple_choice",
                "answer": "A", "answer_index": 1}
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web') as search, \
                patch.object(monitor, 'chat') as chat:
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        self.assertEqual(text, json.dumps(plan))
        search.assert_not_called()
        chat.assert_not_called()

    def test_no_search_flag_and_connectivity_check_skip_search(self):
        plan = {"found": True, "needs_search": True, "search_query": "q",
                "question_type": "written", "answer": None,
                "question": "Q", "response": "A"}
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web') as search, \
                patch.object(monitor, 'chat') as chat:
            monitor.answer_with_search(b'png', 'test-key', 'm', use_search=False)
            monitor.answer_with_search(None, 'test-key', 'm')
        search.assert_not_called()
        chat.assert_not_called()

    def test_unparseable_plan_skips_search(self):
        with patch.object(monitor, 'ask_deepseek',
                          return_value=('not json', 'stop')), \
                patch.object(monitor, 'search_web') as search:
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        self.assertEqual(text, 'not json')
        search.assert_not_called()

    def test_empty_search_results_keep_first_answer(self):
        plan = {"found": True, "question_type": "written", "answer": None,
                "question": "Q", "response": "first",
                "needs_search": True, "search_query": "q"}
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web', return_value=[]), \
                patch.object(monitor, 'chat') as chat:
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        self.assertEqual(text, json.dumps(plan))
        chat.assert_not_called()

    def test_grounding_failure_or_malformed_answer_keeps_first_answer(self):
        plan = {"found": True, "question_type": "multiple_choice", "answer": "A",
                "answer_index": 1, "question": "Q", "needs_search": True,
                "search_query": "q"}
        results = [{"title": "T", "url": "https://example.com/a", "summary": "S"}]
        for final in (urllib.error.URLError('down'),
                      ('{broken', 'stop'),
                      ('{"found":true,"answer":"Z"}', 'stop')):
            with self.subTest(final=final), \
                    patch.object(monitor, 'ask_deepseek',
                                 return_value=(json.dumps(plan), 'stop')), \
                    patch.object(monitor, 'search_web', return_value=results), \
                    patch.object(monitor, 'chat') as chat:
                if isinstance(final, Exception):
                    chat.side_effect = final
                else:
                    chat.return_value = final
                text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
            self.assertEqual(text, json.dumps(plan))

    def test_letter_wins_over_conflicting_index(self):
        plan = {"found": True, "question_type": "multiple_choice", "answer": "A",
                "answer_index": 1, "options": ["old", "new"], "question": "Q",
                "needs_search": True, "search_query": "q"}
        grounded = {"found": True, "question_type": "multiple_choice",
                    "answer": "B", "answer_index": 1, "response": "B is newer"}
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web',
                             return_value=[{"url": "https://e.example",
                                            "summary": "S"}]), \
                patch.object(monitor, 'chat',
                             return_value=(json.dumps(grounded), 'stop')):
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        result = monitor.parse_result(text)
        self.assertEqual(result['answer'], 'B')
        self.assertEqual(result['answer_index'], 2)
        self.assertEqual(result['options'], ['old', 'new'])
        self.assertEqual(result['response'], 'B is newer')

    def test_labelled_options_are_accepted_and_cleaned(self):
        plan = {"found": True, "question_type": "multiple_choice", "answer": "A",
                "answer_index": 1, "options": ["old", "new"], "question": "Q",
                "needs_search": True, "search_query": "q"}
        grounded = {"found": True, "question_type": "multiple_choice",
                    "answer": "B", "answer_index": 2,
                    "options": ["A) old", "B) new"], "question": "Q",
                    "response": "newer"}
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web',
                             return_value=[{"url": "https://e.example",
                                            "summary": "S"}]), \
                patch.object(monitor, 'chat',
                             return_value=(json.dumps(grounded), 'stop')):
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        result = monitor.parse_result(text)
        self.assertEqual(result['options'], ['old', 'new'])
        self.assertEqual(result['answer_index'], 2)

    def test_full_transcription_is_kept_when_grounded_shortens_it(self):
        plan = {"found": True, "question_type": "multiple_choice", "answer": "A",
                "answer_index": 1, "options": ["old", "new"],
                "question": "Q\nA) old\nB) new"}
        grounded = {"found": True, "question_type": "multiple_choice",
                    "answer": "B", "options": ["old", "new"], "question": "Q",
                    "response": "x"}
        result = monitor.reconcile_grounded(plan, json.dumps(grounded))
        self.assertEqual(result["question"], plan["question"])
        self.assertEqual(result["answer_index"], 2)
        self.assertEqual(result["answer"], "B")

    def test_rewritten_options_discard_grounded_answer(self):
        plan = {"found": True, "question_type": "multiple_choice", "answer": "A",
                "answer_index": 1, "options": ["old", "new"], "question": "Q",
                "needs_search": True, "search_query": "q"}
        grounded = {"found": True, "question_type": "multiple_choice",
                    "answer": "A", "options": ["new", "old"], "question": "Q"}
        with patch.object(monitor, 'ask_deepseek',
                          return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web',
                             return_value=[{"url": "https://e.example",
                                            "summary": "S"}]), \
                patch.object(monitor, 'chat',
                             return_value=(json.dumps(grounded), 'stop')):
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        self.assertEqual(text, json.dumps(plan))

    def test_search_web_returns_empty_on_network_error(self):
        with patch.object(monitor.urllib.request, 'urlopen',
                          side_effect=urllib.error.URLError('offline')), \
                patch.object(monitor.time, 'sleep'):
            self.assertEqual(monitor.search_web('anything', 'test-key'), [])

    def test_search_web_does_not_retry_client_errors(self):
        error = urllib.error.HTTPError(monitor.SEARCH_URL, 400, 'Bad Request', {},
                                       io.BytesIO(b'bad'))
        with patch.object(monitor.urllib.request, 'urlopen',
                          side_effect=error) as opener, \
                patch.object(monitor.time, 'sleep'):
            self.assertEqual(monitor.search_web('q', 'test-key'), [])
        self.assertEqual(opener.call_count, 1)

    def test_search_context_drops_items_without_a_summary(self):
        context = monitor.format_search_context([
            {"title": "with", "url": "https://a.example", "summary": "text"},
            {"title": "without", "url": "https://b.example"}])
        self.assertIn('https://a.example', context)
        self.assertNotIn('https://b.example', context)

    def test_low_integrity_hotkey_start_is_refused(self):
        with patch.object(monitor, 'integrity_level', return_value='low'), \
                patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), \
                patch.object(monitor.sys, 'argv', ['monitor.py', '--key', 'f9']), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(monitor.main(), 2)
        self.assertIn('low integrity', out.getvalue())
        self.assertIn('start.cmd', out.getvalue())

    def test_low_integrity_does_not_block_capture_modes(self):
        data = {"found": False, "question_type": "none", "answer": None,
                "question": "", "response": "nothing"}
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(monitor, 'integrity_level', return_value='low'), \
                patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key'}), \
                patch.object(monitor.sys, 'argv',
                             ['monitor.py', '--once', '--mute', '--answer-file',
                              str(Path(folder, 'a.txt'))]), \
                patch.object(monitor, 'capture_silent',
                             return_value=(b'png', 'abc', None)), \
                patch.object(monitor, 'answer_with_search',
                             return_value=(json.dumps(data), 'stop')), \
                patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(monitor.main(), 0)

    def test_popup_setting_can_change_while_running(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Path(folder, '.monitor-settings')
            self.assertTrue(monitor.popup_enabled(settings))  # no file yet
            settings.write_text('2', encoding='utf-8-sig')
            self.assertFalse(monitor.popup_enabled(settings))
            settings.write_text('1', encoding='utf-8')
            self.assertTrue(monitor.popup_enabled(settings))

    def test_popup_receives_position_and_scale(self):
        result = {"question_type": "multiple_choice", "answer": "B",
                  "options": ["one", "two"]}
        with patch.object(monitor.sys, 'platform', 'win32'), \
                patch.object(monitor, 'load_settings',
                             return_value={'popup': 'on',
                                           'position': 'top-right',
                                           'scale': '150'}), \
                patch.object(monitor.subprocess, 'Popen') as popen:
            monitor.show_answer_popup(result)
        argv = popen.call_args.args[0]
        self.assertIn('--corner=top-right', argv)
        self.assertIn('--scale=150', argv)
        self.assertIn('--title=Answer: B', argv)
        self.assertIn('--layout=compact', argv)

    def test_written_answer_popup_keeps_the_whole_paragraph(self):
        long_answer = ('Perizinan terpadu memangkas waktu proses karena semua '
                       'instansi memeriksa satu berkas yang sama. Investor cukup '
                       'mengunggah dokumen sekali, lalu status tiap izin terlihat '
                       'di satu dasbor. Perubahan kecil seperti ini yang membuat '
                       'proses terasa jauh lebih cepat bagi pengguna.')
        result = {"question_type": "written", "answer": None,
                  "question": "Jelaskan perbaikan proses perizinan.",
                  "response": long_answer}
        with patch.object(monitor.sys, 'platform', 'win32'), \
                patch.object(monitor, 'load_settings',
                             return_value={'popup': 'on',
                                           'position': 'bottom-left',
                                           'scale': '100'}), \
                patch.object(monitor.subprocess, 'Popen') as popen:
            monitor.show_answer_popup(result)
        argv = popen.call_args.args[0]
        detail = [a for a in argv if a.startswith('--detail=')][0]
        self.assertIn('--layout=paragraph', argv)
        self.assertEqual(detail, '--detail=' + long_answer)

    def test_written_answers_are_asked_to_stay_short(self):
        self.assertIn('short and to the point', monitor.SYSTEM_PROMPT)

    def test_clipboard_text_for_multiple_choice(self):
        result = {"question_type": "multiple_choice", "answer": "B",
                  "answer_index": 2, "options": ["2 1/2", "2 3/4", "3 1/4"]}
        self.assertEqual(monitor.clipboard_text(result), "B. 2 3/4")

    def test_clipboard_text_for_written_answer(self):
        result = {"question_type": "written", "answer": None,
                  "response": "  Perizinan terpadu memangkas waktu.  "}
        self.assertEqual(monitor.clipboard_text(result),
                         "Perizinan terpadu memangkas waktu.")

    def test_clipboard_text_keeps_line_breaks_in_essays(self):
        result = {"question_type": "written", "answer": None,
                  "response": "a. Perizinan terpadu.\nb. Investor -> Portal."}
        self.assertEqual(monitor.clipboard_text(result),
                         "a. Perizinan terpadu.\nb. Investor -> Portal.")
    def test_clipboard_text_is_empty_without_an_answer(self):
        self.assertEqual(monitor.clipboard_text({"question_type": "none"}), "")
        self.assertEqual(monitor.clipboard_text(
            {"question_type": "multiple_choice", "answer": None}), "")

    def test_clipboard_text_falls_back_to_the_letter(self):
        result = {"question_type": "multiple_choice", "answer": "c",
                  "answer_index": 9, "options": ["one", "two"]}
        self.assertEqual(monitor.clipboard_text(result), "C")
    def test_popup_duration_comes_from_settings(self):
        result = {"question_type": "multiple_choice", "answer": "A",
                  "options": ["one", "two"]}
        with patch.object(monitor.sys, 'platform', 'win32'), \
                patch.object(monitor, 'load_settings',
                             return_value={'popup': 'on',
                                           'position': 'bottom-left',
                                           'scale': '100',
                                           'duration': '5',
              }), \
                patch.object(monitor.subprocess, 'Popen') as popen:
            monitor.show_answer_popup(result)
        self.assertIn('--duration-ms=5000', popen.call_args.args[0])

    def test_popup_duration_falls_back_when_garbage(self):
        result = {"question_type": "multiple_choice", "answer": "A",
                  "options": ["one", "two"]}
        with patch.object(monitor.sys, 'platform', 'win32'), \
                patch.object(monitor, 'load_settings',
                             return_value={'popup': 'on',
                                           'position': 'bottom-left',
                                           'scale': '100',
                                           'duration': 'abc',
              }), \
                patch.object(monitor.subprocess, 'Popen') as popen:
            monitor.show_answer_popup(result)
        self.assertIn('--duration-ms=2000', popen.call_args.args[0])


    def test_settings_file_parses_position_and_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Path(folder, '.monitor-settings')
            settings.write_text('popup=off\nposition=top-right\nscale=150\n'
                                'thinking=max\n', encoding='utf-8')
            loaded = monitor.load_settings(settings)
        self.assertEqual(loaded, {'popup': 'off', 'position': 'top-right',
                                  'scale': '150', 'thinking': 'max',
                                  'duration': '2'})

    def test_thinking_defaults_to_high(self):
        with tempfile.TemporaryDirectory() as folder:
            loaded = monitor.load_settings(Path(folder, 'missing'))
        self.assertEqual(loaded['thinking'], 'high')

    def test_chat_payload_thinking_modes(self):
        captured = {}

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(req, timeout=None):
            captured['body'] = json.loads(req.data.decode('utf-8'))
            return FakeResponse(json.dumps(
                {"choices": [{"finish_reason": "stop",
                              "message": {"content": "{}"}}]}).encode())

        def run(thinking, base='https://api.deepseek.com'):
            with patch.dict(os.environ, {'DEEPSEEK_BASE_URL': base}), \
                    patch.object(monitor, 'load_settings',
                                 return_value={'popup': 'on',
                                               'position': 'bottom-left',
                                               'scale': '100',
                                               'thinking': thinking}), \
                    patch.object(monitor.urllib.request, 'urlopen',
                                 side_effect=fake_urlopen):
                monitor.chat('k', 'deepseek-flash', [{'role': 'user', 'content': 'x'}])
            return captured['body']

        body = run('max')
        self.assertEqual(body['thinking'], {'type': 'enabled'})
        self.assertEqual(body['reasoning_effort'], 'max')
        self.assertEqual(body['max_tokens'], 8192)
        self.assertNotIn('temperature', body)

        body = run('off')
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['max_tokens'], 4096)
        self.assertEqual(body['temperature'], 0)

        body = run('high', base='https://api.example.com/v1')
        self.assertNotIn('thinking', body)
        self.assertNotIn('reasoning_effort', body)
        self.assertEqual(body['temperature'], 0)

    def test_settings_file_defaults_and_unknown_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Path(folder, '.monitor-settings')
            settings.write_text('# comment\nposition=center\nnonsense=1\n',
                                encoding='utf-8')
            loaded = monitor.load_settings(settings)
        self.assertEqual(loaded['position'], 'center')
        self.assertEqual(loaded['popup'], 'on')
        self.assertEqual(loaded['scale'], '100')

    def test_api_base_can_be_overridden(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DEEPSEEK_BASE_URL', None)
            self.assertEqual(monitor.api_base(), 'https://api.deepseek.com')
            self.assertTrue(monitor.deepseek_hosted())
            os.environ['DEEPSEEK_BASE_URL'] = 'https://api.example.com/v1/'
            self.assertEqual(monitor.api_base(), 'https://api.example.com/v1')
            self.assertFalse(monitor.deepseek_hosted())

    def test_third_party_endpoint_skips_deepseek_search(self):
        plan = {"found": False, "question_type": "none", "answer": None,
                "question": "", "response": "nothing", "needs_search": True,
                "search_query": "q"}
        with patch.dict(os.environ, {'DEEPSEEK_BASE_URL': 'https://api.example.com/v1'}), \
                patch.object(monitor, 'ask_deepseek',
                             return_value=(json.dumps(plan), 'stop')), \
                patch.object(monitor, 'search_web') as search:
            text, _ = monitor.answer_with_search(b'png', 'test-key', 'm')
        self.assertEqual(text, json.dumps(plan))
        search.assert_not_called()

    def test_no_search_option_and_env_reach_answer_with_search(self):
        for argv_extra, env in ((['--no-search'], {}),
                                ([], {'DEEPSEEK_SEARCH': 'off'})):
            with self.subTest(argv=argv_extra, env=env), \
                    tempfile.TemporaryDirectory() as folder, \
                    patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-key', **env}), \
                    patch.object(monitor.sys, 'argv',
                                 ['monitor.py', '--once', '--mute', *argv_extra,
                                  '--answer-file', str(Path(folder, 'a.txt'))]), \
                    patch.object(monitor, 'capture_silent',
                                 return_value=(b'png', 'abc', None)), \
                    patch.object(monitor, 'answer_with_search',
                                 return_value=('{"found":true,"answer":"B"}', 'stop')) as answer, \
                    patch.object(monitor, 'signal_answer'), \
                    patch.object(monitor.time, 'sleep'), \
                    patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(monitor.main(), 0)
                self.assertFalse(answer.call_args.kwargs['use_search'])



if __name__ == '__main__':
    unittest.main()
