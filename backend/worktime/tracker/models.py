from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField('email address', unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

class Tag(models.Model):
    nome = models.CharField(max_length=100)
    ore = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    creato = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('nome',),)

    def __str__(self):
        return self.nome


class Project(models.Model):
    nome = models.CharField(max_length=200)
    responsabile = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    tags = models.ManyToManyField(Tag, blank=True, related_name='projects')

    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Progetto'
        verbose_name_plural = 'Progetti'

class TimeEntry(models.Model):
    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entries')
    progetto = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='entries')
    descrizione = models.CharField(max_length=500, blank=True)
    tipo_ticket = models.CharField(max_length=100, blank=True, null=True)
    inizio = models.DateTimeField(default=timezone.now)
    fine = models.DateTimeField(null=True, blank=True)

    @property
    def duration(self):
        if self.fine:
            return self.fine - self.inizio
        return timezone.now() - self.inizio

    def __str__(self):
        return f"{self.utente} - {self.progetto or 'No project'} @ {self.inizio.isoformat()}"

    class Meta:
        verbose_name = 'Attività'
        verbose_name_plural = 'Attività'