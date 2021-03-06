import re
import os
import sys
import tempfile
import logging
from django.core import serializers, management
from django.db import (models, transaction, router, DEFAULT_DB_ALIAS,
        DatabaseError, IntegrityError)
from avocado.models import DataField, DataConcept, DataConceptField, DataCategory

FIXTURE_FORMAT = 'json'
FIXTURE_FILENAME_RE = re.compile(r'^[0-9]{4}_[0-9a-zA-Z_]+(\.json)$')

MIGRATION_MODEL_LABELS = ('avocado.datafield', 'avocado.dataconcept',
    'avocado.dataconceptfield', 'avocado.datacategory')

log = logging.getLogger(__name__)


def _fixture_filenames(dirname):
    filenames = []
    for f in os.listdir(dirname):
        if FIXTURE_FILENAME_RE.match(os.path.basename(f)):
            filenames.append(f)
    filenames.sort()
    return filenames


def next_fixture_name(name, dirname):
    filenames = _fixture_filenames(dirname)
    if not filenames:
        version = '0001'
    else:
        version = str(int(filenames[-1][:4]) + 1).zfill(4)
    return '{0}_{1}'.format(version, name)


def full_fixture_path(name):
    return '{0}.{1}'.format(os.path.join(get_fixture_dir(), name), FIXTURE_FORMAT)


def get_fixture_dir():
    from avocado.conf import settings
    fixture_dir = settings.METADATA_FIXTURE_DIR
    if fixture_dir:
        return fixture_dir
    app = models.get_app(settings.METADATA_MIGRATION_APP)
    if hasattr(app, '__path__'):
        # It's a 'models/' subpackage
        app_dir = os.path.dirname(os.path.dirname(app.__file__))
    else:
        # It's a models.py module
        app_dir = os.path.dirname(app.__file__)
    return os.path.join(app_dir, 'fixtures')


def create_fixture(name, using=DEFAULT_DB_ALIAS, silent=False):
    "Dumps data in the fixture format optionally to a particular path."
    if os.path.isabs(name):
        fixture_path = name
    else:
        fixture_path = full_fixture_path(name)
    with open(fixture_path, 'w') as fout:
        management.call_command('dumpdata', *MIGRATION_MODEL_LABELS,
            database=using, stdout=fout)
    if not silent:
        log.info('Created fixture {0}'.format(name))


def create_temp_fixture(*args, **kwargs):
    "Creates a fixture to a temporary file."
    fh, path = tempfile.mkstemp() 
    create_fixture(path, *args, **kwargs)
    return path


def load_fixture(name, using=DEFAULT_DB_ALIAS):
    """Progammatic way to load a fixture given some path. This does not
    assume the path is a fixture within some app and assumes a full path.
    """
    if os.path.isabs(name):
        fixture_path = name
    else:
        fixture_path = full_fixture_path(name)

    with open(fixture_path) as fixture:
        objects = serializers.deserialize(FIXTURE_FORMAT, fixture, using=using)

        with transaction.commit_manually(using):
            for obj in objects:
                if router.allow_syncdb(using, obj.object.__class__):
                    try:
                        obj.save(using=using)
                    except (DatabaseError, IntegrityError), e:
                        transaction.rollback(using)
                        msg = 'Could not load {app_label}.{object_name}(pk={pk}): {error_msg}'\
                            .format(app_label=obj.object._meta.app_label,
                                object_name=obj.object._meta.object_name,
                                pk=obj.object.pk, error_msg=e)
                        raise e.__class__, e.__class__(msg), sys.exc_info()[2]
            transaction.commit(using)
    log.info('Loaded data from fixture {0}'.format(name))


def delete_metadata(using=DEFAULT_DB_ALIAS):
    "Deletes all metadata in the target database."
    DataConceptField.objects.using(using).delete()
    DataConcept.objects.using(using).delete()
    DataField.objects.using(using).delete()
    DataCategory.objects.using(using).delete()
    log.debug('Metadata deleted from database "{0}"'.format(using))


def safe_load(name, backup_path=None, using=DEFAULT_DB_ALIAS):
    """Creates a backup of the current state of the metadata, attempts to load
    the new fixture and falls back to the backup fixture if the load fails for
    any reason.
    """
    with transaction.commit_manually(using):
        # Create the backup fixture 
        if backup_path:
            create_fixture(os.path.abspath(backup_path), using=using, silent=True)
        else:
            backup_path = create_temp_fixture(using=using, silent=True)
        log.info('Backup fixture written to {0}'.format(os.path.abspath(backup_path)))
        delete_metadata(using=using)
        try:
            load_fixture(name, using=using)
        except (DatabaseError, IntegrityError):
            transaction.rollback(using)
            log.error('Fixture load failed, reverting from backup: {0}'.format(backup_path))
            load_fixture(backup_path, using=using)
            raise
        transaction.commit(using)
    return backup_path
