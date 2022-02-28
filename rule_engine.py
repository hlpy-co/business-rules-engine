from business_rule_engine import RuleParser, Rule
import os
import logging
import traceback
from collections import OrderedDict
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')


class RuleEngine:

    def __init__(self):
        self.parser = RuleParser()
        self.register_function(print)
        self.ordered_rules = []

    @staticmethod
    def __read_text_file__(file_path):
        with open(file_path, 'r') as f:
            return f.read()

    @staticmethod
    def is_excluded(rule, exclusions):
        for exclusion in exclusions:
            conds = "".join(rule.conditions)
            result = re.search(f'event\s*=\s*["|\']{exclusion}["|\']', conds)
            logging.debug(f'checking [{conds}] wrt [{f"event={exclusion}"}]. Result [{result}]')
            if result:
                return True
        return False

    @staticmethod
    def and_operator(conditions: []):
        if len(conditions) == 0:
            return conditions
        conds = ",\n".join(conditions)

        result = f'AND({conds})'
        return result

    @staticmethod
    def get_priority(ordered_rules):
        return ordered_rules["priority"]

    def register_function(self, function):
        self.parser.register_function(function)

    def load_rules_from_folder(self, rule_folder):
        for file in os.listdir(path=rule_folder):
            if os.path.isdir(f"{rule_folder}/{file}"):
                self.load_rules_from_folder(f"{rule_folder}/{file}")
            else:
                rule = self.__read_text_file__(f"{rule_folder}/{file}")
                self.add_rule_from_string(rule)

    def process(self, params):
        variables = {}
        exclusions = []

        def set_variable(key, value):
            variables[key] = value

        def get_variable(key):
            return variables[key] if key in variables.keys() else None

        def get_context():
            return variables

        def exclude(event):
            exclusions.append(event)

        self.parser.register_function(set_variable)
        self.parser.register_function(get_variable)
        self.parser.register_function(get_context)
        self.parser.register_function(exclude)

        for rule in self.ordered_rules:
            try:
                logging.debug(f"exclusions: [{exclusions}]")
                if not self.is_excluded(rule['rule'], exclusions) and rule['rule'].rulename not in exclusions:
                    rule['rule'].execute(params)
                else:
                    logging.info(f"rule [{rule['rule'].rulename}] is excluded")
            except Exception as e:
                traceback.print_exc()
                logging.error(e)

        return variables

    def add_rules(self, rules):
        for r in rules:
            self.add_rule(r)

    def add_rule(self, rule):
        r = Rule(rule['name'])
        conditions = self.and_operator(rule['conditions']) \
            if isinstance(rule['conditions'], list) \
            else rule['conditions']
        actions = self.and_operator(rule['actions']) if isinstance(rule['actions'], list) else rule['actions']
        r.conditions.append(conditions)
        r.actions.append(actions)
        self.add_rule_to_knowledge(r, priority=rule['priority'])

    def remove_rule(self, rule_name):
        for r in self.ordered_rules:
            if r['rule'].rulename == rule_name:
                self.ordered_rules.remove(r)
                break

    def get_rule(self, rule):
        for r in self.ordered_rules:
            if r['rule'].rulename == rule['rule'].rulename:
                return r
        return None

    def add_rule_to_knowledge(self, rule: Rule, priority=1000):
        r = {"rule": rule, "priority": priority}
        old_rule = self.get_rule(r)
        if old_rule:
            self.ordered_rules.remove(old_rule)
        self.ordered_rules.append(r)
        self.ordered_rules.sort(key=self.get_priority)
        return True

    def add_rule_from_string(self, rule):
        self.parser.parsestr(rule)
        for key in self.parser.rules:
            value = self.parser.rules[key]
            self.add_rule_to_knowledge(value)
        self.parser.rules = OrderedDict()
