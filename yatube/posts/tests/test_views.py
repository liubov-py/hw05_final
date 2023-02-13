import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post

User = get_user_model()


def context_assert(self, context):
    self.assertEqual(context.text, self.post.text)
    self.assertEqual(context.author, self.post.author)
    self.assertEqual(context.group, self.post.group)
    self.assertEqual(context.pub_date, self.post.pub_date)
    self.assertEqual(context.image, self.post.image.name)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUserViews')

        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded
        )

        cls.NAME_INDEX = reverse('posts:index')
        cls.NAME_GROUP_LIST = reverse('posts:group_list',
                                      kwargs={'slug': cls.group.slug})
        cls.NAME_PROFILE = reverse('posts:profile',
                                   kwargs={'username': cls.user.username})
        cls.NAME_POST_DETAIL = reverse('posts:post_detail',
                                       kwargs={'post_id': cls.post.id})
        cls.NAME_CREATE = reverse('posts:post_create')
        cls.NAME_POST_EDIT = reverse('posts:post_edit',
                                     kwargs={'post_id': cls.post.id})

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        cache.clear()

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_page_names = {
            self.NAME_INDEX: 'posts/index.html',
            self.NAME_GROUP_LIST: 'posts/group_list.html',
            self.NAME_PROFILE: 'posts/profile.html',
            self.NAME_POST_DETAIL: 'posts/post_detail.html',
            self.NAME_CREATE: 'posts/create_post.html',
            self.NAME_POST_EDIT: 'posts/create_post.html'
        }

        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(self.NAME_INDEX)
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        context = response.context['page_obj'][0]
        context_assert(self, context)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(self.NAME_GROUP_LIST)
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        context = response.context['page_obj'][0]
        group = response.context['group']
        self.assertEqual(group, self.group)
        context_assert(self, context)

    def test_profile_show_correct_context(self):
        """Шаблон  сформирован с правильным контекстом."""
        response = self.guest_client.get(self.NAME_PROFILE)
        object = response.context['author']
        self.assertEqual(object, self.user)
        context = response.context['page_obj'][0]
        context_assert(self, context)

    def test_post_detail_show_correct_context(self):
        """Шаблон  сформирован с правильным контекстом."""
        response = self.guest_client.get(self.NAME_POST_DETAIL)
        context = response.context['post']
        context_assert(self, context)

    def test_create_post_show_correct_context(self):
        """Шаблон  сформирован с правильным контекстом."""
        response = self.authorized_client.get(self.NAME_CREATE)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон  сформирован с правильным контекстом."""
        response = self.authorized_client.get(self.NAME_POST_EDIT)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_added_correctly(self):
        """Пост при создании добавлен корректно"""
        post = Post.objects.create(
            text='Тестовый текст проверка как добавился',
            author=self.user,
            group=self.group)
        response_index = self.authorized_client.get(self.NAME_INDEX)
        response_group = self.authorized_client.get(self.NAME_GROUP_LIST)
        response_profile = self.authorized_client.get(self.NAME_PROFILE)
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        self.assertIn(post, index)
        self.assertIn(post, group)
        self.assertIn(post, profile)

    def test_post_not_added_another_user(self):
        """Пост при создании не добавляется другому пользователю
           Но виден на главной и в группе"""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        post = Post.objects.create(
            text='Тестовый текст проверка как добавился',
            author=self.user,
            group=self.group)
        response_group = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': group2.slug})
        )
        group = response_group.context['page_obj']
        self.assertNotIn(post, group)

    def test_comment_added_on_post_detail(self):
        comment = Comment.objects.create(
            text='Комментарий',
            author=self.user,
            post=self.post
        )
        response_post_detail = self.authorized_client.get(
            self.NAME_POST_DETAIL)
        detail = response_post_detail.context['comments']
        self.assertIn(comment, detail)

    def test_index_cache(self):
        posts_count_0 = Post.objects.count()
        post = Post.objects.create(
            text='Тестовый текст для проверки кеша',
            author=self.user,
            group=self.group)
        response_index_0 = self.authorized_client.get(self.NAME_INDEX)
        self.assertEqual(Post.objects.count(), posts_count_0 + 1)
        post.delete()
        response_index_1 = self.authorized_client.get(self.NAME_INDEX)
        self.assertEqual(response_index_0.content, response_index_1.content)
        cache.clear()
        response_index_2 = self.authorized_client.get(self.NAME_INDEX)
        self.assertNotEqual(response_index_0.content, response_index_2.content)

    def test_follow(self):
        author = User.objects.create_user(username='TestUserFollow')
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': author.username})
        )
        follow = Follow.objects.filter(
            author=author,
            user=self.user
        ).exists()
        self.assertTrue(follow)

    def test_unfollow(self):
        author = User.objects.create_user(username='TestUserFollow')
        Follow.objects.create(
            user=self.user,
            author=author
        )
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': author.username})
        )
        unfollow = Follow.objects.filter(
            author=author,
            user=self.user
        ).exists()
        self.assertFalse(unfollow)

    def test_404_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        template = 'core/404.html'
        response = self.guest_client.get('post/bl.html')
        self.assertTemplateUsed(response, template)


class PaginatorViewsTest(TestCase):
    # Здесь создаются фикстуры: клиент и 13 тестовых записей.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUserPaginator')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        posts_list: list = []
        for i in range(0, 13):
            posts_list.append(Post(text=f'Тестовый текст {i}',
                                   group=cls.group,
                                   author=cls.user))
        Post.objects.bulk_create(posts_list)

        # Создаем неавторизованный клиент
        cls.guest_client = Client()
        cls.NAME_INDEX = reverse('posts:index')
        cls.NAME_GROUP_LIST = reverse('posts:group_list',
                                      kwargs={'slug': cls.group.slug})
        cls.NAME_PROFILE = reverse('posts:profile',
                                   kwargs={'username': cls.user.username})

    def setUp(self):
        cache.clear()

    def test_page_contains_rigth_records(self):
        pages = (self.NAME_INDEX,
                 self.NAME_PROFILE,
                 self.NAME_GROUP_LIST)

        for page in pages:
            response = self.guest_client.get(page)
            # Проверка: количество постов на первой странице равно 10
            self.assertEqual(len(response.context['page_obj']),
                             settings.PER_PAGE)
            # Проверка: на второй странице должно быть три поста.
            response = self.guest_client.get(page + '?page=2')
            count = len(response.context['page_obj']) % settings.PER_PAGE
            self.assertEqual(len(response.context['page_obj']), count)
