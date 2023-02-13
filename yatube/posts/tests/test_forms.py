import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоватьсяgs
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUserForms')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )
        cls.NAME_CREATE = reverse('posts:post_create')
        cls.NAME_POST_EDIT = reverse('posts:post_edit',
                                     kwargs={'post_id': cls.post.id})
        cls.NAME_LOGIN = reverse('users:login')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Модуль shutil - библиотека Python с удобными инструментами
        # для управления файлами и директориями:
        # создание, удаление, копирование, перемещение,
        # изменение папок и файлов
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_new_post_in_db(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Текст из формы',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            self.NAME_CREATE,
            data=form_data,
            follow=True
        )
        # Убедимся, что запись в базе данных создалась:
        # сравним количество записей до и после отправки формы
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image, 'posts/' + uploaded.name)

    def test_edit_post(self):
        # Создадим еще одну группу для проверки
        # изменения группы при редактировании
        group2 = Group.objects.create(title='Тестовая группа2',
                                      slug='test_group',
                                      description='Описание')
        form_data = {'text': 'Текст отредактированный',
                     'group': group2.id}
        response = self.authorized_client.post(
            self.NAME_POST_EDIT,
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, 200)
        post_new = Post.objects.get(id=self.post.id)
        self.assertEqual(post_new.text, form_data['text'])
        self.assertEqual(post_new.group.id, form_data['group'])
        self.assertEqual(post_new.author, self.user)
        self.assertEqual(post_new.id, self.post.id)

    def test_redirect_new_post_guest_client(self):
        posts_count = Post.objects.count()
        form_data = {'text': 'Текст неавторизованного пользователя',
                     'group': self.group.id}
        response = self.guest_client.post(
            self.NAME_CREATE,
            data=form_data,
            follow=True)
        self.assertRedirects(
            response, self.NAME_LOGIN + '?next=' + self.NAME_CREATE)
        self.assertEqual(Post.objects.count(), posts_count)


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUserComment')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )
        cls.NAME_ADD_COMMENT = reverse('posts:add_comment',
                                       kwargs={'post_id': cls.post.id})
        cls.NAME_POST_DETAIL = reverse('posts:post_detail',
                                       kwargs={'post_id': cls.post.id})
        cls.NAME_LOGIN = reverse('users:login')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_comment_added_by_authorized_client(self):
        comment_count = Comment.objects.count()
        form_data = {'text': 'Комментарий'}
        response = self.authorized_client.post(
            self.NAME_ADD_COMMENT,
            data=form_data,
            follow=True)
        self.assertRedirects(
            response, self.NAME_POST_DETAIL)
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)

    def test_comment_added_by_guest_client(self):
        comment_count = Comment.objects.count()
        form_data = {'text': 'Комментарий'}
        response = self.guest_client.post(
            self.NAME_ADD_COMMENT,
            data=form_data,
            follow=True)
        self.assertRedirects(
            response, self.NAME_LOGIN + '?next=' + self.NAME_ADD_COMMENT)
        self.assertEqual(Comment.objects.count(), comment_count)
