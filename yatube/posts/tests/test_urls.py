from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post

User = get_user_model()


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='TestUser')
        cls.user2 = User.objects.create_user(username='TestUser2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user1,
            text='Тестовый пост'
        )
        cls.URL_INDEX = '/'
        cls.URL_GROUP_LIST = f'/group/{cls.group.slug}/'
        cls.URL_PROFILE = f'/profile/{cls.user2.username}/'
        cls.URL_POST_DETAIL = f'/posts/{cls.post.id}/'
        cls.URL_CREATE = '/create/'
        cls.URL_POST_EDIT = f'/posts/{cls.post.id}/edit/'
        cls.URL_404 = '/core/404.html'
        cls.URL_403csrf = '/core/403csrf.html'

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user2)
        self.author_client = Client()
        self.author_client.force_login(self.user1)

    def test_url_response_guest(self):
        # Проверяем доступность страниц для неавторизованного пользователя
        url_names = {
            'index': self.URL_INDEX,
            'group_list': self.URL_GROUP_LIST,
            'profile': self.URL_PROFILE,
            'post_detail': self.URL_POST_DETAIL
        }

        for address in url_names.values():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_response_unexisting_page(self):
        # Проверяем код ответа для несущестующей страницы
        response = self.authorized_client.get('/page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_response_authorized(self):
        # Проверяем доступность страниц для авторизованного пользователя
        response = self.authorized_client.get(self.URL_CREATE)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_response_author(self):
        # Проверяем доступность страниц для автора поста
        pages = (self.URL_CREATE,
                 self.URL_POST_EDIT)
        for page in pages:
            response = self.author_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_redirect_anonymous_on_admin_login(self):
        # Проверяем доступность страниц для автора поста
        response1 = self.guest_client.get(self.URL_POST_EDIT)
        response2 = self.authorized_client.get(self.URL_POST_EDIT)
        self.assertRedirects(
            response1, f'/auth/login/?next=/posts/{self.post.id}/edit/')
        self.assertRedirects(
            response2, f'/auth/login/?next=/posts/{self.post.id}/edit/')

    def test_url_redirect_anonymous_on_admin_login(self):
        """Страница создания поста перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get(self.URL_CREATE, follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/')

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            self.URL_INDEX: 'posts/index.html',
            self.URL_GROUP_LIST: 'posts/group_list.html',
            self.URL_PROFILE: 'posts/profile.html',
            self.URL_POST_DETAIL: 'posts/post_detail.html',
            self.URL_CREATE: 'posts/create_post.html',
            self.URL_POST_EDIT: 'posts/create_post.html'
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_404_page(self):
        response = self.guest_client.get(self.URL_404)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
