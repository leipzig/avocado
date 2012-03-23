from optparse import make_option

from django.db.models import (get_model, get_models, get_app, AutoField,
    ForeignKey, OneToOneField, ManyToManyField)
from django.core.management.base import LabelCommand

from avocado.models import Field, Category

class Command(LabelCommand):
    """
    SYNOPSIS::

        python manage.py avocado sync [options...] labels...

    DESCRIPTION:

        Finds all models referenced by the app or model ``labels`` and
        attempts to create a ``Field`` instance per model field.
        Any ``Field`` already loaded will not be altered in any way.

    OPTIONS:

        ``--create-categories`` - Create a single ``Category`` corresponding to each
        model that is evaluated.

        ``--include-non-editable`` - Create ``Field`` instances for fields marked
        as not editable (i.e. ``editable=False``).

        ``--include-keys`` - Create ``Field`` instances for primary key
        and foreign key fields.

        ``--update`` - Updates existing ``Field`` instances with metadata from
        model fields. Note this overwrites any descriptive metadata changes made
        to ``Field`` such as ``name``, ``name_plural``, and ``description``.

    """

    help = """Finds all models in the listed app(s) and attempts to create a
    ``Field`` instance per model field. Fields already declared will
    not be altered.
    """

    args = '<app app app.model ...>'

    option_list = LabelCommand.option_list + (
        make_option('--create-categories', action='store_true',
            dest='create_categories', default=False,
            help='Create a category for each model'),

        make_option('--include-non-editable', action='store_true',
            dest='include_non_editable', default=False,
            help='Create fields for non-editable fields'),

        make_option('--include-keys', action='store_true',
            dest='include_keys', default=False,
            help='Create fields for primary and foreign key fields'),

        make_option('--update', action='store_true',
            dest='update_existing', default=False,
            help='Updates existing metadata derived from model fields'),
    )

    # these are ignored since these join fields will be determined at runtime
    # using the modeltree library. fields can be created for any other
    # these field types manually
    key_field_types = (
        AutoField,
        ForeignKey,
        OneToOneField,
    )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self._categories = {}

    def _get_category(self, model):
        if model not in self._categories:
            category, is_new = Category.objects.get_or_create(name=model._meta.verbose_name)
            self._categories[model] = category
        return self._categories[model]

    def handle_label(self, label, **options):
        "Handles app_label or app_label.model_label formats."
        labels = label.split('.')
        models = None
        create_categories = options.get('create_categories')
        include_non_editable = options.get('include_non_editable')
        include_keys = options.get('include_keys')
        update_existing = options.get('update_existing')

        if update_existing:
            resp = raw_input('Are you sure you want to update existing metadata? '
                'This will overwrite any previous changes made. Type "yes" to continue.')
            if resp.lower() != 'yes':
                print 'Sync operation cancelled'
                return

        # a specific model is defined
        if len(labels) == 2:
            # attempts to find the model given the app and model labels
            model = get_model(*labels)

            if model is None:
                print 'Cannot find model "%s", skipping...' % label
                return

            models = [model]

        # get all models for the app
        else:
            app = get_app(*labels)
            models = get_models(app)

            if models is None:
                print 'Cannot find app "%s", skipping...' % label
                return

        app_name = labels[0]

        for model in models:
            new_count = 0
            update_count = 0
            model_name = model._meta.object_name.lower()
            category = self._get_category(model) if create_categories else None

            for field in model._meta.fields:
                if isinstance(field, ManyToManyField):
                    continue

                # Check for primary key, and foreign key fields
                if isinstance(field, self.key_field_types) and not include_keys:
                    continue

                # Ignore non-editable fields since in most cases they are for
                # managment purposes
                if not field.editable and not include_non_editable:
                    continue

                # All but the field name is case-insensitive, do initial lookup
                # to see if it already exists, skip if it does
                lookup = {
                    'app_name__iexact': app_name,
                    'model_name__iexact': model_name,
                    'field_name': field.name,
                }

                try:
                    field = Field.objects.get(**lookup)
                except Field.DoesNotExist:
                    field = None

                kwargs = {
                    'name': field.verbose_name.title(),
                    'name_plural': field.verbose_name.title() + 's',
                    'description': field.help_text,
                    'app_name': app_name.lower(),
                    'model_name': model_name.lower(),
                    'field_name': field.name,
                    'category': category,
                }

                if field:
                    if not update_existing:
                        print '(%s) %s.%s already exists. Skipping...' % (app_name, model_name, field.name)
                        continue
                    # Only overwrite if the source value is not falsy
                    field.__dict__.update([(k, v) for k, v in kwargs.items() if v])
                    update_count += 1
                else:
                    field = Field(**kwargs)
                    field.published = False
                    new_count += 1

                field.save()


            if new_count == 1:
                print '1 field added for %s' % model_name
            elif new_count > 1:
                print '%d fields added for %s' % (new_count, model_name)

            if update_count == 1:
                print '1 field updated for %s' % model_name
            elif update_count > 1:
                print '%d fields updated for %s' % (update_count, model_name)
