"""Tests for intent_extractor and QueryClassifier.get_query_intent (no network; the LLM is mocked).
Run: python -m unittest test_intent_extractor -v"""
import unittest
from unittest import mock

import intent_extractor as ie
from query_classifier import QueryClassifier


def llm_returns(content):
    resp = mock.Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {'choices': [{'message': {'content': content}}]}
    return mock.patch.object(ie.requests, 'post', return_value=resp)


class FindServersTest(unittest.TestCase):
    def models(self, q):
        return [m for m, _ in ie.find_servers(q)]

    def test_plain_and_prefixed(self):
        self.assertEqual(self.models("When did we stop supporting the S924?"), ['S924'])
        self.assertEqual(self.models("When is the IBM Power E980 withdrawn?"), ['E980'])
        self.assertEqual(self.models("activation features for the s1022"), ['S1022'])

    def test_g_variant_is_not_the_base_model(self):
        self.assertEqual(self.models("S924-G lifecycle"), ['S924-G'])
        self.assertEqual(self.models("S924 G lifecycle"), ['S924-G'])
        self.assertEqual(self.models("S924 gets withdrawn when?"), ['S924'])

    def test_lc_and_l_are_different(self):
        self.assertEqual(self.models("LC922 support"), ['LC922'])
        self.assertEqual(self.models("L922 support"), ['L922'])

    def test_mtm_token(self):
        self.assertEqual(ie.find_servers("9242-21T availability"), [('S1112', '9242-21T')])
        self.assertEqual(ie.find_servers("9009-42A"), [('S924', '9009-42A')])

    def test_not_a_server(self):
        self.assertEqual(ie.find_servers("What is a Power server?"), [])
        self.assertEqual(ie.find_servers("the 922 box"), [])
        self.assertEqual(ie.find_servers("E9800"), [])


class ValidateTest(unittest.TestCase):
    def test_invented_server_is_dropped(self):
        r = ie.validate_llm_result({'server_model': 'S9999', 'query_type': 'bogus',
                                    'lifecycle_field': 'nope', 'candidates': ['E980', 'X1']})
        self.assertIsNone(r['server_model'])
        self.assertIsNone(r['query_type'])
        self.assertIsNone(r['lifecycle_field'])
        self.assertEqual(r['candidates'], ['E980'])

    def test_mtm_and_name_are_normalised(self):
        self.assertEqual(ie.validate_llm_result({'server_model': '9009-42A'})['server_model'], 'S924')
        self.assertEqual(ie.validate_llm_result({'server_model': 'IBM Power s924'})['server_model'], 'S924')

    def test_search_query_is_cleaned_and_optional(self):
        r = ie.validate_llm_result({'search_query': '  maximum   memory\ncapacity TB '})
        self.assertEqual(r['search_query'], 'maximum memory capacity TB')
        self.assertIsNone(ie.validate_llm_result({'search_query': 'x'})['search_query'])
        self.assertIsNone(ie.validate_llm_result({'search_query': 42})['search_query'])
        self.assertIsNone(ie.validate_llm_result({})['search_query'])


class RetrievalScopeTest(unittest.TestCase):
    def setUp(self):
        self.c = QueryClassifier(use_watson=False)

    def scope(self, q):
        return self.c.retrieval_scope(q)

    def test_feature_codes_and_part_numbers_are_feature_scope(self):
        for q in ("What is feature code #EFP1?", "Is (#0010) still available on the E980?",
                  "What is feature code 5899?", "Which feature codes are memory DIMMs on the S1022?",
                  "What is the CCIN for the NVMe drive?"):
            self.assertEqual(self.scope(q), 'feature', q)

    def test_general_questions_are_general_scope(self):
        for q in ("What is the maximum memory of the E980?", "Which operating systems does the S1022 support?",
                  "How much power does the E980 use?", "What are the dimensions and weight of the S924?",
                  "How many PCIe slots does the S1024 have?"):
            self.assertEqual(self.scope(q), 'general', q)

    def test_orderable_options_are_mixed_scope(self):
        for q in ("What PCIe adapters can I order for the S1022?", "What are the key features of the E980?",
                  "Which memory options are there for the S1024?"):
            self.assertEqual(self.scope(q), 'mixed', q)

    def test_intent_carries_the_scope(self):
        with mock.patch.object(ie, 'LLM_BASE_URL', ''):
            self.assertEqual(self.c.get_query_intent("What is the maximum memory of the E980?")['retrieval_scope'],
                             'general')
            self.assertEqual(self.c.get_query_intent("What is feature code #EFP1 on the E980?")['retrieval_scope'],
                             'feature')


class IntentTest(unittest.TestCase):
    def setUp(self):
        self.c = QueryClassifier(use_watson=False)

    def test_clear_lifecycle_question_needs_no_llm(self):
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), \
                mock.patch.object(ie.requests, 'post') as post:
            i = self.c.get_query_intent("When is the E980 withdrawn?")
        post.assert_not_called()
        self.assertEqual((i['query_type'], i['server_model'], i['lifecycle_field']),
                         ('table_lookup', 'E980', 'withdrawn'))

    def test_stop_supporting(self):
        i = self.c.get_query_intent("When did we stop supporting the S924?")
        self.assertEqual((i['query_type'], i['server_model'], i['lifecycle_field']),
                         ('table_lookup', 'S924', 'end_of_support'))

    def test_deterministic_only_without_llm(self):
        with mock.patch.object(ie, 'LLM_BASE_URL', ''):
            i = self.c.get_query_intent("S1112 lifecycle")
        self.assertEqual(i['server_model'], 'S1112')
        self.assertEqual(i['source'], 'deterministic')

    def test_llm_reads_free_text(self):
        reply = '{"server_model": "S924", "candidates": [], "query_type": "table_lookup", "lifecycle_field": "end_of_support"}'
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), llm_returns(reply):
            i = self.c.get_query_intent("My customer has the S9 twenty four, is IBM done supporting it?")
        self.assertEqual((i['query_type'], i['server_model'], i['lifecycle_field'], i['source']),
                         ('table_lookup', 'S924', 'end_of_support', 'llm'))

    def test_llm_cannot_override_exact_server(self):
        reply = '{"server_model": "E980", "query_type": "rag", "lifecycle_field": null}'
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), llm_returns(reply):
            i = self.c.get_query_intent("Tell me about the S1022 memory")
        self.assertEqual(i['server_model'], 'S1022')

    def test_activation_regex_hit_is_kept(self):
        reply = '{"server_model": "S1022", "query_type": "rag", "lifecycle_field": null}'
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), llm_returns(reply):
            i = self.c.get_query_intent("What processor activation features does the S1022 have?")
        self.assertEqual((i['query_type'], i['server_model']), ('activation_lookup', 'S1022'))

    def test_llm_failure_falls_back(self):
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), \
                mock.patch.object(ie.requests, 'post', side_effect=ie.requests.ConnectionError('down')):
            i = self.c.get_query_intent("activation features for the S1022")
        self.assertEqual(i['server_model'], 'S1022')
        self.assertEqual(i['source'], 'deterministic')

    def test_bare_s924_asks_a_or_g(self):
        i = self.c.get_query_intent("When did we stop supporting the S924?")
        self.assertEqual([o['mtm'] for o in i['mtm_options']], ['9009-42A', '9009-42G'])

    def test_explicit_variant_or_mtm_does_not_ask(self):
        for q in ("When did we stop supporting the S924-G?", "When did we stop supporting the 9009-42A?"):
            self.assertEqual(self.c.get_query_intent(q)['mtm_options'], [], q)

    def test_model_without_variants_does_not_ask(self):
        self.assertEqual(self.c.get_query_intent("When is the E980 withdrawn?")['mtm_options'], [])
        self.assertEqual(self.c.get_query_intent("When is the S1112 withdrawn?")['mtm_options'], [])

    def test_two_dates_in_one_question_go_to_the_llm(self):
        reply = '{"server_model": "E980", "query_type": "table_lookup", "lifecycle_field": "withdrawn"}'
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), llm_returns(reply) as post:
            i = self.c.get_query_intent("The E980 was available in 2018, when was it withdrawn?")
        post.assert_called_once()
        self.assertEqual(i['lifecycle_field'], 'withdrawn')

    def test_two_dates_without_llm_asks_which_date(self):
        with mock.patch.object(ie, 'LLM_BASE_URL', ''):
            i = self.c.get_query_intent("The E980 was available in 2018, when was it withdrawn?")
        self.assertIsNone(i['lifecycle_field'])

    def test_typo_goes_to_the_llm(self):
        reply = '{"server_model": "E980", "query_type": "table_lookup", "lifecycle_field": "withdrawn"}'
        with mock.patch.object(ie, 'LLM_BASE_URL', 'http://x'), llm_returns(reply) as post:
            i = self.c.get_query_intent("wen was the E980 witdrawn from markt?")
        post.assert_called_once()
        self.assertEqual((i['server_model'], i['lifecycle_field']), ('E980', 'withdrawn'))

    def test_no_server_asks_for_clarification(self):
        with mock.patch.object(ie, 'LLM_BASE_URL', ''):
            i = self.c.get_query_intent("When was it withdrawn?")
        self.assertIsNone(i['server_model'])
        self.assertTrue(i['needs_clarification'])


if __name__ == '__main__':
    unittest.main()
