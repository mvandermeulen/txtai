"""
Embeddings+database module tests
"""

import os
import tempfile
import unittest

from txtai.embeddings import Embeddings
from txtai.database import Database, SQLException
from txtai.vectors import WordVectors


class TestEmbeddings(unittest.TestCase):
    """
    Embeddings with a database tests
    """

    @classmethod
    def setUpClass(cls):
        """
        Initialize test data.
        """

        cls.data = [
            "US tops 5 million confirmed virus cases",
            "Canada's last fully intact ice shelf has suddenly collapsed, forming a Manhattan-sized iceberg",
            "Beijing mobilises invasion craft along coast as Taiwan tensions escalate",
            "The National Park Service warns against sacrificing slower friends in a bear attack",
            "Maine man wins $1M from $25 lottery ticket",
            "Make huge profits without work, earn up to $100,000 a day",
        ]

        # Create embeddings model, backed by sentence-transformers & transformers
        cls.embeddings = Embeddings({"path": "sentence-transformers/nli-mpnet-base-v2", "content": True})

    def testData(self):
        """
        Test content storage and retrieval
        """

        data = self.data + [{"date": "2021-01-01", "text": "Baby panda", "flag": 1}]

        # Create an index for the list of text
        self.embeddings.index([(uid, text, None) for uid, text in enumerate(data)])

        # Search for best match
        result = self.embeddings.search("feel good story", 1)[0]
        self.assertEqual(result["text"], data[-1]["text"])

    def testDelete(self):
        """
        Test delete
        """

        # Create an index for the list of text
        self.embeddings.index([(uid, text, None) for uid, text in enumerate(self.data)])

        # Delete best match
        self.embeddings.delete([4])

        # Search for best match
        result = self.embeddings.search("feel good story", 1)[0]

        self.assertEqual(self.embeddings.count(), 5)
        self.assertEqual(result["text"], self.data[5])

    def testIndex(self):
        """
        Test index
        """

        # Create an index for the list of text
        self.embeddings.index([(uid, text, None) for uid, text in enumerate(self.data)])

        # Search for best match
        result = self.embeddings.search("feel good story", 1)[0]

        self.assertEqual(result["text"], self.data[4])

    def testNotImplemented(self):
        """
        Tests exceptions for non-implemented methods
        """

        database = Database({})

        self.assertRaises(NotImplementedError, database.load, None)
        self.assertRaises(NotImplementedError, database.insert, None)
        self.assertRaises(NotImplementedError, database.delete, None)
        self.assertRaises(NotImplementedError, database.save, None)
        self.assertRaises(NotImplementedError, database.ids, None)
        self.assertRaises(NotImplementedError, database.resolve, None, None)
        self.assertRaises(NotImplementedError, database.embed, None, None)
        self.assertRaises(NotImplementedError, database.query, None, None)

    def testSave(self):
        """
        Test save
        """

        # Create an index for the list of text
        self.embeddings.index([(uid, text, None) for uid, text in enumerate(self.data)])

        # Generate temp file path
        index = os.path.join(tempfile.gettempdir(), "embeddings")

        self.embeddings.save(index)
        self.embeddings.load(index)

        # Search for best match
        result = self.embeddings.search("feel good story", 1)[0]

        self.assertEqual(result["text"], self.data[4])

        # Test offsets still work after save/load
        self.embeddings.upsert([(0, "Test insert", None)])
        self.assertEqual(self.embeddings.count(), len(self.data))

    def testSQL(self):
        """
        Test running a SQL query
        """

        # Create an index for the list of text
        self.embeddings.index([(uid, text, None) for uid, text in enumerate(self.data)])

        # Test similar
        result = self.embeddings.search(
            "select * from txtai where similar('feel good story') group by text having count(*) > 0 order by score desc", 5
        )[0]
        self.assertEqual(result["text"], self.data[4])

        # Test where
        result = self.embeddings.search("select * from txtai where text like '%iceberg%'", 1)[0]
        self.assertEqual(result["text"], self.data[1])

        # Test count
        result = self.embeddings.search("select count(*) from txtai")[0]
        self.assertEqual(list(result.values())[0], len(self.data))

        # Test columns
        result = self.embeddings.search("select id, text, data, entry from txtai")[0]
        self.assertEqual(sorted(result.keys()), ["data", "entry", "id", "text"])

        # Test SQL parse error
        with self.assertRaises(SQLException):
            self.embeddings.search("select * from txtai where bad,query")

    def testUpsert(self):
        """
        Test upsert
        """

        # Build data array
        data = [(uid, text, None) for uid, text in enumerate(self.data)]

        # Reset embeddings for test
        self.embeddings.ann = None

        # Create an index for the list of text
        self.embeddings.upsert(data)

        # Update data
        data[0] = (0, "Feel good story: baby panda born", None)
        self.embeddings.upsert([data[0]])

        # Search for best match
        result = self.embeddings.search("feel good story", 1)[0]

        self.assertEqual(result["text"], data[0][1])

    def testWords(self):
        """
        Test embeddings backed by word vectors
        """

        # Initialize model path
        path = os.path.join(tempfile.gettempdir(), "model")
        os.makedirs(path, exist_ok=True)

        # Build tokens file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as output:
            tokens = output.name
            for x in self.data:
                output.write(x + "\n")

        # Word vectors path
        vectors = os.path.join(path, "test-10d")

        # Build word vectors, if they don't already exist
        WordVectors.build(tokens, 10, 1, vectors)

        # Create dataset
        data = [(x, row, None) for x, row in enumerate(self.data)]

        # Create embeddings model, backed by word vectors
        embeddings = Embeddings(
            {"path": vectors + ".magnitude", "storevectors": True, "scoring": "bm25", "pca": 3, "quantize": True, "content": True}
        )

        # Call scoring and index methods
        embeddings.score(data)
        embeddings.index(data)

        # Test search
        self.assertIsNotNone(embeddings.search("win", 1))

        # Generate temp file path
        index = os.path.join(tempfile.gettempdir(), "wembeddings")

        # Test save/load
        embeddings.save(index)
        embeddings.load(index)

        # Test search
        self.assertIsNotNone(embeddings.search("win", 1))
