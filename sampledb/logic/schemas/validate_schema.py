# coding: utf-8
"""
Implementation of validate_schema(schema)
"""


import datetime
import typing
import urllib.parse
import re

from ..errors import ValidationError
from .utils import units_are_valid
from .validate import validate

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def validate_schema(schema: dict, path: typing.Optional[typing.List[str]] = None) -> None:
    """
    Validates the given schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    if path is None:
        path = []
    if not isinstance(schema, dict):
        raise ValidationError('invalid schema (must be dict)', path)
    if 'type' not in schema:
        raise ValidationError('invalid schema (must contain type)', path)
    if not isinstance(schema['type'], str):
        raise ValidationError('invalid schema (type must be str)', path)
    if 'title' not in schema:
        raise ValidationError('invalid schema (must contain title)', path)
    if not isinstance(schema['title'], str):
        raise ValidationError('invalid schema (title must be str)', path)
    if path == [] and schema['type'] != 'object':
        raise ValidationError('invalid schema (root must be an object)', path)
    if schema['type'] == 'array':
        return _validate_array_schema(schema, path)
    elif schema['type'] == 'object':
        return _validate_object_schema(schema, path)
    elif schema['type'] == 'text':
        return _validate_text_schema(schema, path)
    elif schema['type'] == 'datetime':
        return _validate_datetime_schema(schema, path)
    elif schema['type'] == 'bool':
        return _validate_bool_schema(schema, path)
    elif schema['type'] == 'quantity':
        return _validate_quantity_schema(schema, path)
    elif schema['type'] == 'sample':
        return _validate_sample_schema(schema, path)
    elif schema['type'] == 'measurement':
        return _validate_measurement_schema(schema, path)
    elif schema['type'] == 'object_reference':
        return _validate_object_reference_schema(schema, path)
    elif schema['type'] == 'tags':
        return _validate_tags_schema(schema, path)
    elif schema['type'] == 'hazards':
        return _validate_hazards_schema(schema, path)
    elif schema['type'] == 'user':
        return _validate_user_schema(schema, path)
    else:
        raise ValidationError('invalid type', path)


def _validate_hazards_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validate the given GHS hazards schema and raise a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if path != ['hazards']:
        raise ValidationError('GHS hazards must be a top-level entry named "hazards"', path)
    if not isinstance(schema.get('note', ''), str):
        raise ValidationError('note must be a string', path)


def _validate_array_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given array schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'items', 'style', 'minItems', 'maxItems', 'default'}
    required_keys = {'type', 'title', 'items'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    has_min_items = False
    if 'minItems' in schema:
        if not isinstance(schema['minItems'], int):
            raise ValidationError('minItems must be an integer', path)
        elif schema['minItems'] < 0:
            raise ValidationError('minItems must not be negative', path)
        else:
            has_min_items = True
    has_max_items = False
    if 'maxItems' in schema:
        if not isinstance(schema['maxItems'], int):
            raise ValidationError('maxItems must be an integer', path)
        elif schema['maxItems'] < 0:
            raise ValidationError('maxItems must not be negative', path)
        else:
            has_max_items = True
    if has_min_items and has_max_items:
        if schema['minItems'] > schema['maxItems']:
            raise ValidationError('minItems must be less than or equal to maxItems', path)
    if 'style' in schema and schema['style'] not in ('table', 'list'):
        raise ValidationError('style must be either "list" or "table"', path)
    validate_schema(schema['items'], path + ['[?]'])
    if 'default' in schema:
        validate(schema['default'], schema, path + ['(default)'])


def _validate_tags_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given tags schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'dataverse_export'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'default' in schema:
        validate({'_type': 'tags', 'tags': schema['default']}, schema, path + ['(default)'])
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if path != ['tags']:
        raise ValidationError('Tags must be a top-level entry named "tags"', path)


def _validate_object_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'properties', 'propertyOrder', 'required', 'default'}
    if not path:
        # the top level object may contain a list of properties to be displayed in a table of objects
        valid_keys.add('displayProperties')
        valid_keys.add('batch')
        valid_keys.add('batch_name_format')
        valid_keys.add('notebookTemplates')
    required_keys = {'type', 'title', 'properties'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if not isinstance(schema['properties'], dict):
        raise ValidationError('properties must be dict', path)
    for property_name, property_schema in schema['properties'].items():
        if '__' in property_name:
            raise ValidationError('invalid property name: {}'.format(property_name), path)
        validate_schema(property_schema, path + [property_name])

    if 'required' in schema:
        if not isinstance(schema['required'], list):
            raise ValidationError('required must be list', path)
        for i, property_name in enumerate(schema['required']):
            if property_name not in schema['properties']:
                raise ValidationError('unknown required property: {}'.format(property_name), path)
            if property_name in schema['required'][:i]:
                raise ValidationError('duplicate required property: {}'.format(property_name), path)

    if 'hazards' in schema['properties'] and schema['properties']['hazards']['type'] == 'hazards' and 'hazards' not in schema.get('required', []):
        raise ValidationError('GHS hazards may not be optional', path)

    if not path:
        if 'name' not in schema['properties'] or schema['properties']['name']['type'] != 'text':
            raise ValidationError('Schema must include a text property "name"', path)
        if 'required' not in schema or 'name' not in schema['required']:
            raise ValidationError('"name" must be a required property for the root object', path)

    if 'propertyOrder' in schema:
        if not isinstance(schema['propertyOrder'], list):
            raise ValidationError('propertyOrder must be list', path)
        for i, property_name in enumerate(schema['propertyOrder']):
            if property_name not in schema['properties']:
                raise ValidationError('unknown propertyOrder property: {}'.format(property_name), path)
            if property_name in schema['propertyOrder'][:i]:
                raise ValidationError('duplicate propertyOrder property: {}'.format(property_name), path)

    if 'default' in schema:
        validate(schema['default'], schema)

    if 'displayProperties' in schema:
        if not isinstance(schema['displayProperties'], list):
            raise ValidationError('displayProperties must be list', path)
        for i, property_name in enumerate(schema['displayProperties']):
            if property_name not in schema['properties']:
                raise ValidationError('unknown display property: {}'.format(property_name), path)
            if property_name in schema['displayProperties'][:i]:
                raise ValidationError('duplicate displayProperties property: {}'.format(property_name), path)

    if 'batch' in schema:
        if not isinstance(schema['batch'], bool):
            raise ValidationError('batch must be bool', path)

    if 'batch_name_format' in schema:
        if not schema.get('batch', False):
            raise ValidationError('batch must be True for batch_name_format to be set', path)
        if not isinstance(schema['batch_name_format'], str):
            raise ValidationError('batch_name_format must be a string', path)
        try:
            schema['batch_name_format'].format(1)
        except (ValueError, KeyError):
            raise ValidationError('invalid batch_name_format', path)

    if 'notebookTemplates' in schema:
        _validate_notebook_templates(schema['notebookTemplates'])


def _validate_text_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given text object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'minLength', 'maxLength', 'choices', 'pattern', 'multiline', 'note', 'placeholder', 'dataverse_export'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema and not isinstance(schema['default'], str):
        raise ValidationError('default must be str', path)
    if 'minLength' in schema and (not isinstance(schema['minLength'], int) or isinstance(schema['minLength'], bool)):
        raise ValidationError('minLength must be int', path)
    if 'maxLength' in schema and (not isinstance(schema['maxLength'], int) or isinstance(schema['maxLength'], bool)):
        raise ValidationError('maxLength must be int', path)
    if 'minLength' in schema and schema['minLength'] < 0:
        raise ValidationError('minLength must not be negative', path)
    if 'maxLength' in schema and schema['maxLength'] < 0:
        raise ValidationError('maxLength must not be negative', path)
    if 'minLength' in schema and 'maxLength' in schema and schema['maxLength'] < schema['minLength']:
        raise ValidationError('maxLength must not be less than minLength', path)
    if 'choices' in schema and not isinstance(schema['choices'], list):
        raise ValidationError('choices must be list', path)
    if 'choices' in schema and not schema['choices']:
        raise ValidationError('choices must not be empty', path)
    if 'choices' in schema:
        for i, choice in enumerate(schema['choices']):
            if not isinstance(choice, str):
                raise ValidationError('choice must be str', path + [str(i)])
            if choice.isspace():
                raise ValidationError('choice must contain more than whitespace', path + [str(i)])
    if 'placeholder' in schema and 'choices' in schema:
        raise ValidationError('placeholder cannot be used together with choices', path)
    if 'placeholder' in schema and not isinstance(schema['placeholder'], str):
        raise ValidationError('placeholder must be str', path)
    if 'pattern' in schema and not isinstance(schema['pattern'], str):
        raise ValidationError('pattern must be str', path)
    if 'pattern' in schema:
        try:
            re.compile(schema['pattern'])
        except re.error:
            raise ValidationError('pattern is no valid regular expression', path)
    if 'multiline' in schema and not isinstance(schema['multiline'], bool):
        raise ValidationError('multiline must be bool', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'dataverse_export' in schema and not schema['dataverse_export'] and path == ['name']:
        raise ValidationError('dataverse_export must be True for the object name', path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)


def _validate_datetime_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given datetime object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'note', 'dataverse_export'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema:
        if not isinstance(schema['default'], str):
            raise ValidationError('default must be str', path)
        else:
            try:
                datetime.datetime.strptime(schema['default'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise ValidationError('invalid default value', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)


def _validate_bool_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given boolean object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'note', 'dataverse_export'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema and not isinstance(schema['default'], bool):
        raise ValidationError('default must be bool', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)


def _validate_quantity_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given quantity object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'units', 'default', 'note', 'placeholder', 'dataverse_export'}
    required_keys = {'type', 'title', 'units'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if not isinstance(schema['units'], str):
        raise ValidationError('units must be str', path)
    elif not units_are_valid(schema['units']):
        raise ValidationError('invalid units', path)

    if 'default' in schema and not isinstance(schema['default'], float) and not isinstance(schema['default'], int):
        raise ValidationError('default must be float or int', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)

    if 'placeholder' in schema and not isinstance(schema['placeholder'], str):
        raise ValidationError('placeholder must be str', path)


def _validate_sample_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given sample object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)


def _validate_measurement_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given measurement object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)


def _validate_object_reference_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given object reference object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'action_type_id', 'action_id', 'dataverse_export'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)
    if 'action_type_id' in schema and not isinstance(schema['action_type_id'], (int, type(None))):
        raise ValidationError('action_type_id must be int or None', path)
    if 'action_id' in schema and not isinstance(schema['action_id'], (int, type(None))):
        raise ValidationError('action_id must be int or None', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)


def _validate_notebook_templates(notebook_templates: typing.Any) -> None:
    """
    Validate the given notebook templates and raise a ValidationError if they are invalid.

    :param notebook_templates: the sampledb object schema
    :raise ValidationError: if the notebook templates are invalid
    """
    if not isinstance(notebook_templates, list):
        raise ValidationError('notebookTemplates must be a list', ['notebookTemplates'])

    for notebook_index, notebook_template in enumerate(notebook_templates):
        path = ['notebookTemplates', str(notebook_index)]
        if not isinstance(notebook_template, dict):
            raise ValidationError('notebook template must be a dict', path)
        valid_keys = {'title', 'url', 'params'}
        required_keys = valid_keys
        schema_keys = set(notebook_template.keys())
        invalid_keys = schema_keys - valid_keys
        if invalid_keys:
            raise ValidationError('unexpected keys in notebook template: {}'.format(invalid_keys), path)
        missing_keys = required_keys - schema_keys
        if missing_keys:
            raise ValidationError('missing keys in notebook template: {}'.format(missing_keys), path)
        if not isinstance(notebook_template['title'], str):
            raise ValidationError('notebook template title must be str', path)
        if not isinstance(notebook_template['url'], str):
            raise ValidationError('notebook template url must be str', path)
        if not notebook_template['url'].endswith('.ipynb'):
            raise ValidationError('notebook template url must end with .ipynb', path)
        base_url = 'https://iffjupyter.fz-juelich.de/templates/t/'
        test_url = urllib.parse.urljoin(base_url, notebook_template['url'])
        if not test_url.startswith(base_url) or urllib.parse.urlparse(base_url).netloc != urllib.parse.urlparse(test_url).netloc:
            raise ValidationError('notebook template url must be relative', path)
        if not isinstance(notebook_template['params'], dict):
            raise ValidationError('notebook template params must be a dict', path)
        for param_name, param_value in notebook_template['params'].items():
            if not isinstance(param_name, str):
                raise ValidationError('notebook template param names must be str', path)
            if not isinstance(param_value, str) and not isinstance(param_value, list):
                raise ValidationError('notebook template param values must be str or a list', path)
            if isinstance(param_value, list):
                for param_step in param_value:
                    if not isinstance(param_step, str) and not isinstance(param_step, int):
                        raise ValidationError('notebook template param value steps must be str or int', path)
            if isinstance(param_value, str):
                valid_param_values = {'object_id'}
                if param_value not in valid_param_values:
                    raise ValidationError('notebook template param value must be a list or one of {}'.format(valid_param_values), path)


def _validate_user_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given user object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'note' in schema and not isinstance(schema['note'], str):
        raise ValidationError('note must be str', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
