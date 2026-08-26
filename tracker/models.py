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
    name = models.CharField(max_length=100)
    # owner removed: tags are global
    color = models.CharField(max_length=7, blank=True, null=True)
    hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('name',),)

    def __str__(self):
        return self.name

    def get_color(self):
        """Return a dict with 'bg' and 'border' colors.

        If `color` is set, use it as background and compute a darker border.
        Otherwise derive defaults from the name (bug -> red, miglioramento/feature -> green).
        """
        def darken_hex(hx, amount=0.28):
            # hx like #RRGGBB
            try:
                hx = hx.lstrip('#')
                r = int(hx[0:2], 16)
                g = int(hx[2:4], 16)
                b = int(hx[4:6], 16)
                r = max(0, int(r * (1 - amount)))
                g = max(0, int(g * (1 - amount)))
                b = max(0, int(b * (1 - amount)))
                return f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                return '#999999'

        if self.color:
            bg = self.color
        else:
            n = (self.name or '').lower()
            if 'bug' in n:
                bg = '#ffecec'  # very light red background
            elif 'miglior' in n or 'improv' in n or 'feature' in n:
                bg = '#f2fff0'  # very light green background
            else:
                bg = '#f3f3f3'  # light gray
        border = darken_hex(bg, amount=0.38)
        return {'bg': bg, 'border': border}


# Palette of light background colors for tag selection (bg hexes)
PALETTE = ['#fff7f7', '#fffaf0', '#f7fff8', '#f0f7ff', '#f7f0ff', '#f7fbff', '#f3f3f3']


class Project(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    tags = models.ManyToManyField(Tag, blank=True, related_name='projects')

    def __str__(self):
        return self.name

class TimeEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entries')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='entries')
    description = models.CharField(max_length=500, blank=True)
    jira_issue_type = models.CharField(max_length=100, blank=True, null=True)
    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(null=True, blank=True)

    @property
    def duration(self):
        if self.end:
            return self.end - self.start
        return timezone.now() - self.start

    def __str__(self):
        return f"{self.user} - {self.project or 'No project'} @ {self.start.isoformat()}"
