import time
import uuid
import pytest
from fe.access import search
from fe.access import auth
from fe.access import seller
from fe import conf
from fe.access.book import BookDB


class TestSearch:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        book_db = BookDB()
        self.books = book_db.get_book_info(0, 10)
        self.user_id = "test_search_user_id_{}".format(str(uuid.uuid1()))
        self.password = "test_search_password_{}".format(str(uuid.uuid1()))
        self.store_id = "test_search_store_id_{}".format(str(uuid.uuid1()))
        self.auth = auth.Auth(conf.URL)
        code = self.auth.register(self.user_id, self.password)
        self.seller = seller.Seller(conf.URL, self.user_id, self.password)
        code = self.seller.create_store(self.store_id)
        self.false_store_id = "test_false_store_id_{}".format(str(uuid.uuid1()))
        for book in self.books:
            code = self.seller.add_book(self.store_id, 0, book)

        self.search = search.Search(conf.URL)
        self.author1 = "test_search_author_{}".format(str(uuid.uuid1()))
        self.author2 = self.books[0].author
        self.book_intro1 = "test_search_book_intro_{}".format(str(uuid.uuid1()))
        self.book_intro2 = self.books[0].book_intro
        self.tags1 = "test_search_tags_{}".format(str(uuid.uuid1()))
        self.tags2 = self.books[0].tags[2]
        self.title1 = "test_search_title_{}".format(str(uuid.uuid1()))
        self.title2 = self.books[0].title
        yield

    def test_search_author(self):
        code = self.search.search_author(self.author1, 1)
        assert code == 200

        code = self.search.search_author(self.author2, 1)
        assert code == 200

        code = self.search.search_author(self.author2, -1)
        assert code == 200

    def test_search_book_intro(self):
        assert self.search.search_book_intro(self.book_intro1, 1) == 200
        assert self.search.search_book_intro(self.book_intro2, 1) == 200
        assert self.search.search_book_intro(self.book_intro2, -1) == 200

    def test_search_tags(self):
        assert self.search.search_tags(self.tags1, 1) == 200
        assert self.search.search_tags(self.tags2, 1) == 200
        assert self.search.search_tags(self.tags2, -1) == 200

    def test_search_title(self):
        assert self.search.search_title(self.title1, 1) == 200
        assert self.search.search_title(self.title2, 1) == 200
        assert self.search.search_title(self.title2, -1) == 200

    def test_search_author_in_store(self):
        assert self.search.search_author_in_store(self.author1, self.store_id, 1) == 200
        assert self.search.search_author_in_store(self.author2, self.store_id, 1) == 200
        assert self.search.search_author_in_store(self.author2, self.store_id, -1) == 200

    def test_search_book_intro_in_store(self):
        assert self.search.search_book_intro_in_store(self.book_intro1, self.store_id, 1) == 200
        assert self.search.search_book_intro_in_store(self.book_intro2, self.store_id, 1) == 200
        assert self.search.search_book_intro_in_store(self.book_intro2, self.store_id, -1) == 200

    def test_search_tags_in_store(self):
        assert self.search.search_tags_in_store(self.title1, self.store_id, 1) == 200
        assert self.search.search_tags_in_store(self.title2, self.store_id, 1) == 200
        assert self.search.search_tags_in_store(self.title2, self.store_id, -1) == 200

    def test_search_title_in_store(self):
        assert self.search.search_title_in_store(self.tags1, self.store_id, 1) == 200
        assert self.search.search_title_in_store(self.tags2, self.store_id, 1) == 200
        assert self.search.search_title_in_store(self.tags2, self.store_id, -1) == 200

    def test_search_author_vague(self):
        assert self.search.search_author("郭", 1) == 200

    def test_search_book_intro_vague(self):
        assert self.search.search_book_intro("传记", 1) == 200

    def test_search_tags_vague(self):
        assert self.search.search_tags("纳什", 1) == 200

    def test_search_title_vague(self):
        assert self.search.search_title("美丽心灵", 1) == 200

    def test_search_author_vague_in_store(self):
        assert self.search.search_author_in_store("娜萨", "书店", 1) == 200

    def test_search_book_intro_vague_in_store(self):
        assert self.search.search_book_intro_in_store("再现", "书店", 1) == 200

    def test_search_tags_vague_in_store(self):
        assert self.search.search_tags_in_store("传记", "书店", 1) == 200

    def test_search_title_vague_in_store(self):
        assert self.search.search_title_in_store("美丽心灵", "书店", 1) == 200
