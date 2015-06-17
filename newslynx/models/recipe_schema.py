import re
import copy

from newslynx.lib import dates
from newslynx.lib import url
from newslynx.lib import mail
from newslynx.lib.stats import parse_number
from newslynx.lib.search import SearchString
from newslynx.lib.serialize import obj_to_json, json_to_obj
from newslynx.models import Recipe
from newslynx.util import gen_short_uuid, update_nested_dict
from newslynx.exc import (
    RecipeSchemaError, SearchStringError)
from newslynx.models.sous_chef_schema import SOUS_CHEF_DEFAULT_OPTIONS
from newslynx.constants import (
    TRUE_VALUES, FALSE_VALUES, NULL_VALUES,
    RECIPE_REMOVE_FIELDS, RECIPE_INTERNAL_FIELDS
)

# order type checking from most to least
# finnicky
TYPE_SORT_ORDER = {
    "email": 0,
    "url": 1,
    "searchstring": 2,
    "datetime": 3,
    "regex": 4,
    "numeric": 5,
    "boolean": 6,
    "string": 7,
    "nulltype": 8
}


def validate(raw_recipe, sous_chef):
    """
    Given a raw recipe and it's associated sous chef,
    validate and parse the recipe.
    """
    uninitialized = raw_recipe.get('status') == 'uninitialized'
    rs = RecipeSchema(raw_recipe, sous_chef, uninitialized)
    return rs.validate()


def update(old_recipe, new_recipe, sous_chef):
    """
    Given a partial or completely new recipe, update the old recipe
    and re-validate it.
    """

    # if the old recipe is a Recipe object, coerce it to and from json.
    if isinstance(old_recipe, Recipe):
        old_recipe = json_to_obj(obj_to_json(old_recipe))

    # format it correctly first.
    _rs = RecipeSchema(new_recipe, sous_chef)
    _rs.format_recipe()
    new_recipe = copy.copy(_rs.recipe)

    # update the previous version.
    new_recipe = update_nested_dict(old_recipe, new_recipe, overwrite=True)

    # revalidate.
    rs = RecipeSchema(new_recipe, sous_chef)
    return rs.validate()


class RecipeSchema(object):

    """
    A class for aiding in recipe option parsing + validation.
    """

    def __init__(self, recipe, sous_chef, uninitialized=False):
        self.recipe = copy.deepcopy(recipe)
        if not 'options' in self.recipe:
            self.recipe['options'] = {}
        self.sous_chef = sous_chef.get('slug')
        self.sous_chef_opts = sous_chef.get('options')
        self.uninitialized = uninitialized

    def get_opt(self, key, top_level=False):
        """
        Get a recipe opt and check for missingness.
        """
        sc_opt = self.sous_chef_opts.get(key)
        if top_level:
            opt = self.recipe.get(key, None)
        else:
            opt = self.recipe['options'].get(key, None)

        if opt is None:
            if sc_opt.get('required', False):

                # check for a default
                if 'default' in sc_opt:
                    return sc_opt.get('default')

                elif self.uninitialized:
                    return None

                raise RecipeSchemaError(
                    "Recipes associated with SousChef '{}'"
                    " require a '{}' option."
                    .format(self.sous_chef, key))
            else:
                return sc_opt.get('default', None)

        return opt

    def valid_nulltype(self, key, opt):
        """

        """
        if opt is None:
            return None
        else:
            try:
                if opt.lower() in NULL_VALUES:
                    return None
            except:
                pass
        return RecipeSchemaError(
            "{} can be a 'nulltype' field but was passed '{}'."
            .format(key, opt))

    def valid_datetime(self, key, opt):
        """
        Validate a iso-datetime option.
        """
        v_opt = dates.parse_iso(opt)
        if not v_opt:
            return RecipeSchemaError(
                "{} can be a 'datetime' field but was passed '{}'."
                .format(key, opt))
        return v_opt

    def valid_searchstring(self, key, opt):
        """
        Validate a searchstring option.
        """
        try:
            return SearchString(opt)
        except SearchStringError as e:
            return RecipeSchemaError(
                "{} can be a 'searchstring' field but was passed '{}'. "
                "Here is the specific error: {}."
                .format(key, opt, e.message))

    def valid_boolean(self, key, opt):
        """
        Validate a boolean option.
        """
        try:
            opt = str(opt)
            if opt.lower() in TRUE_VALUES:
                return True
            if opt.lower() in FALSE_VALUES:
                return False
        except:
            return RecipeSchemaError(
                "{} is an 'boolean' field but was passed '{}'."
                .format(key, opt))

    def valid_numeric(self, key, opt):
        """
        Validate a numeric option.
        """
        try:
            return parse_number(opt)
        except:
            return RecipeSchemaError(
                "{} is an 'numeric' field but was passed '{}'."
                .format(key, opt))

    def valid_string(self, key, opt):
        """
        Validate a string field.
        """
        try:
            return unicode(opt)
        except:
            return RecipeSchemaError(
                "{} can be a 'string' field but was passed '{}'."
                .format(key, opt))

    def valid_url(self, key, opt):
        """
        Validate a url field.
        """
        if url.validate(opt):
            return opt
        return RecipeSchemaError(
            "{} can be a 'url' field but was passed '{}'."
            .format(key, opt))

    def valid_email(self, key, opt):
        """
        Validate a email field.
        """
        if mail.validate(opt):
            return opt
        return RecipeSchemaError(
            "{} can be an 'email' field but was passed '{}'."
            .format(key, opt))

    def valid_regex(self, key, opt):
        """
        Validate a email field.
        """
        try:
            return re.compile(opt)
        except:
            return RecipeSchemaError(
                "{} can be a 'regex' field but was passed '{}'."
                .format(key, opt))

    def validate_type(self, key, opt, type):
        """
        Validate any option type.
        """
        fx_lookup = {
            "string": self.valid_string,
            "numeric": self.valid_numeric,
            "email": self.valid_email,
            "url": self.valid_url,
            "regex": self.valid_regex,
            "boolean": self.valid_boolean,
            "datetime": self.valid_datetime,
            "nulltype": self.valid_nulltype,
            "searchstring": self.valid_searchstring
        }
        return fx_lookup.get(type)(key, opt)

    def validate_types(self, key, opt, types):
        """
        Validate an option that accepts 1 or more types.
        """
        error_messages = []

        # order types by proper check order
        types.sort(key=lambda val: TYPE_SORT_ORDER[val])

        # check types
        for type in types:
            ret = self.validate_type(key, opt, type)
            if isinstance(ret, RecipeSchemaError):
                error_messages.append(ret.message)
            else:
                return ret
        raise RecipeSchemaError(
            "There was problem validating '{}'. "
            "Here are the errors: \n\t- {}"
            .format(key, "\n\t- ".join(error_messages)))

    def validate_opt(self, key, top_level=False):
        """
        Validate any option.
        """
        sc_opt = self.sous_chef_opts.get(key)
        types = sc_opt.get('value_types')
        opt = self.get_opt(key, top_level=top_level)

        # opts that have been coerced to null here
        # should just be returned.
        if opt is None:
            return None

        # validate options which accept lists
        if isinstance(opt, list):
            if not sc_opt.get('accepts_list', False):
                raise RecipeSchemaError(
                    "{} does not accept multiple inputs."
                    .format(key))
            opts = []
            for o in opt:
                o = self.validate_types(key, o, types)
                opts.append(o)
            return opts

        # validate simple options
        return self.validate_types(key, opt, types)

    def format_recipe(self):
        """
        Make sure recipe items are in the right place.
        """
        # remove all internal fields.
        for key in RECIPE_REMOVE_FIELDS:
            self.recipe.pop(key, None)

        # make sure default options are not in `options`.
        for key in self.recipe['options'].keys():
            if key in SOUS_CHEF_DEFAULT_OPTIONS.keys():
                self.recipe[key] = self.recipe['options'].pop(key)

        # make sure recipe options are in `options`
        for key in self.recipe.keys():
            if key not in SOUS_CHEF_DEFAULT_OPTIONS.keys() and\
               key not in RECIPE_INTERNAL_FIELDS and\
               key != 'options':

                self.recipe['options'][key] = self.recipe.pop(key)

        # make sure no non-sc fields are in options
        for key in self.recipe['options'].keys():
            if key not in self.sous_chef_opts:
                self.recipe['options'].pop(key, None)

    def update_sous_chef_defaults(self):
        """
        Merge in sous chef defaults.
        """
        for key in SOUS_CHEF_DEFAULT_OPTIONS.keys():
            # if the key is in the recipe
            # validate it and add in back in.
            if key in self.recipe:
                self.recipe[key] = self.validate_opt(key, top_level=True)

            # otherwise, merge it in.
            else:
                # if the key can be a slug, fall back on the sous chef
                # slug and add a random hash.
                if key == 'slug':
                    slug = "{}-{}".format(self.sous_chef, gen_short_uuid())
                    self.recipe['slug'] = slug
                else:
                    self.recipe[key] = self.validate_opt(key, top_level=True)

    def validate_schedule(self):
        """
        Validate recipe schedule options.
        """
        # check if recipe has time_of_day and interval set. in this case
        # we won't be able to tell what type of schedule it should have.
        if (self.recipe.get('time_of_day') and self.recipe.get('interval')):
            raise RecipeSchemaError(
                "A recipe cannot have 'time_of_day' and 'interval' set.")

        # check if a recipe should be scheduled.
        if not (self.recipe.get('time_of_day') or self.recipe.get('interval')) \
                or self.uninitialized:
            self.recipe['scheduled'] = False

        else:
            self.recipe['scheduled'] = True

    def validate(self):
        """
        Validate a recipe.
        """
        # format it
        self.format_recipe()

        # merge in sous chef defaults.
        self.update_sous_chef_defaults()

        # validate and parse the options:
        for key in self.sous_chef_opts.keys():
            if key not in SOUS_CHEF_DEFAULT_OPTIONS.keys():
                self.recipe['options'][key] = self.validate_opt(key)

        # validate the schedule
        self.validate_schedule()

        # return the valid recipe
        return copy.copy(self.recipe)