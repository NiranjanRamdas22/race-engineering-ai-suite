import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'projects/f1-knowledge-chatbot/f1_knowledge_chatbot'
spec=importlib.util.spec_from_file_location('knowledge_database',FOLDER/'database.py');dbmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(dbmod)
class ChatbotTests(unittest.TestCase):
    def setUp(self):self.db=dbmod.F1Database()
    def test_unknown_winner_question_abstains(self):
        for q in ('Who won the 2024 football World Cup?', 'Who won the 2024 Atlantis Grand Prix?'):
            with self.subTest(q=q):self.assertFalse(self.db.query_driver_or_season(q)['available'])
    def test_races_sharing_a_circuit_keep_distinct_identity(self):
        result=self.db.query_driver_or_season('Who won the 2020 Styrian Grand Prix?')
        self.assertIn('Hamilton',result['answer']);self.assertIn('Styrian',result['answer'])
        self.assertIn('/2020/2/',result['sources'][0]['url'])
    def test_unsupported_year_does_not_answer_other_year(self):
        result=self.db.query_driver_or_season('Who won the 2027 drivers championship?')
        self.assertIsNotNone(result);self.assertIn('unavailable',result['answer'].lower());self.assertNotIn('2023',result['answer'])
    def test_race_winner_not_season_champion(self):
        result=self.db.query_driver_or_season('Who won Monaco in 2024?');self.assertIn('Leclerc',result['answer']);self.assertNotIn('Verstappen',result['answer'])
    def test_specific_constructor_points(self):
        result=self.db.query_driver_or_season('How many points did Ferrari score in 2023?');self.assertIsNotNone(result);self.assertIn('406',result['answer'])
    def test_teammate_qualifying_has_paired_sources(self):
        result=self.db.query_driver_or_season('Compare Hamilton and Russell teammate qualifying in 2024')
        self.assertIn('paired_sessions',result);self.assertGreater(result['paired_sessions'],15);self.assertEqual(len(result['source_sessions']),result['paired_sessions']);self.assertIn('exclusions',result)
    def test_unrelated_query_does_not_route_to_numeric_answer(self):
        self.assertIsNone(self.db.query_driver_or_season('What is the weather in Tokyo?'))
    def test_unrelated_retrieval_abstains(self):
        spec=importlib.util.spec_from_file_location('knowledge_retriever',FOLDER/'retriever.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        r=m.F1Retriever()
        self.assertEqual(r.retrieve_context('What is the weather in Tokyo?'),[])
if __name__=='__main__':unittest.main()

