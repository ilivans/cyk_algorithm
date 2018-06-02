import re
import itertools


class CFG:
    _re_symbol = re.compile("[a-z]|[A-Z]\d*")
    _re_variable = re.compile("[A-Z]\d*")

    @staticmethod
    def _check_variable(s):
        if re.fullmatch(CFG._re_variable, s) is None:
            raise ValueError(s + " - unknown variable")

    @staticmethod
    def _check_symbol(s):
        if re.fullmatch(CFG._re_symbol, s) is None:
            raise ValueError(s + " - unknown symbol")

    def _add_symbol(self, s):
        if s[0].islower():
            self._terminals.add(s)
        else:
            self._variables.add(s)

    def __init__(self, lines: list):
        if not isinstance(lines, list):
            raise TypeError("Need a list of rules for Grammar constructor")
        self._terminals = set()
        self._variables = set()
        # Rules (A -> abc | de | /empty word/ ) store in way: _rules['A'] = { 'a+b+c', 'd+e', '' } .
        self._rules = {}

        if len(lines) == 0:
            raise ValueError("no rules")

        self._start = lines[0].split()[0]
        CFG._check_variable(self._start)
        for line in lines:
            left, *right = line.split()
            CFG._check_variable(left)
            self._add_symbol(left)
            for symbol in right:
                CFG._check_symbol(symbol)
                self._add_symbol(symbol)
            if left not in self._rules:
                self._rules[left] = set()
            self._rules[left].add('+'.join(right))


class CNF(CFG):
    def __init__(self, lines: list):
        super().__init__(lines)
        self._number = 0
        self._character = "A"
        # we won't store epsilon-rules, therefore we pick out the parse of empty word
        self._empty_word = False

        self._eliminate_epsilon_rules()
        self._eliminate_unit_rules()
        self._eliminate_remaining_unacceptable_rules()

    def _generate_variable(self):
        if self._number >= 99 and ord(self._character) < ord('Z'):
            self._character = chr(ord(self._character) + 1)
            self._number = 0
        while (self._character + str(self._number)) in self._variables:
            self._number += 1
        var = self._character + str(self._number)
        self._variables.add(var)
        return var

    def _eliminate_epsilon_rules(self):
        vars_to_inspect = set(self._variables)
        while len(vars_to_inspect) != 0:
            new_vars_to_inspect = set()
            # Going throw all rules to find epsilon rule,
            # if it was found at least once, we need to inspect all rules again
            # after the end of the current inspection, because new epsilon rules could appear.
            for var0 in vars_to_inspect:
                words0 = self._rules[var0]
                if "" in words0:
                    if var0 == self._start:
                        self._empty_word = True
                    words0.remove("")
                    if len(words0) == 0:
                        # Case when var0 produced only empty word.
                        del self._rules[var0]
                        self._variables.remove(var0)
                        for var, words in self._rules.items():
                            # Find right-sides that contain var0 and remove var0 from them.
                            for word in words.copy():
                                word_list = word.split('+')
                                if var0 in word_list:
                                    while var0 in word_list:
                                        word_list.remove(var0)
                                    words.remove(word)   # old rule with var0
                                    words.add('+'.join(word_list))   # new rule without var0
                            if "" in words:
                                new_vars_to_inspect.add(var)
                    else:
                        # Case when var0 produces something except empty word.
                        for var, words in self._rules.items():
                            for word in words.copy():
                                word_list = word.split('+')
                                if var0 in word_list:
                                    # Generate all possible subsets of var0's indices in word
                                    # and add rules with these masks ( A->aXbXXc and var0==X :
                                    # A->abc, A->aXbc, A->abXc (2), A->aXbXc (2), A->abXXc, A->aXbXXc ) .
                                    # Note that duplicates (like A->abXc or A->aXbXc) will merge in set
                                    # and original rule (A->aXbXXc) just won't be removed,
                                    # so we don't need to generate empty mask for original rule.
                                    indices = [i for i, x in enumerate(word_list) if x == var0]
                                    indices_set = set(indices)
                                    for i in range(1, len(indices) + 1):
                                        subsets = set(itertools.combinations(indices_set, i))
                                        for subset in subsets:
                                            ordered_indices = sorted(subset, reverse=True)
                                            copy = list(word_list)
                                            for index in ordered_indices:
                                                del copy[index]
                                            new_word = '+'.join(copy)
                                            if new_word != "" or var != var0:
                                                words.add(new_word)
                                            if new_word == "":
                                                new_vars_to_inspect.add(var)
            vars_to_inspect = new_vars_to_inspect

    def _eliminate_unit_rules(self):
        for var, words in self._rules.items():
            children = set()
            for word in words:
                if CNF._is_single_variable(word):
                    children.add(word)
            words.difference_update(children)
            words.update(self._recursive_descent(children))

    @staticmethod
    def _is_single_variable(word):
        if '+' not in word and word[0].isupper():
            return True
        else:
            return False

    def _recursive_descent(self, children: set):
        if len(children) == 0:
            return set()
        words_to_return = set()
        for child in children:
            words = self._rules[child]
            grandchildren = set()
            for word in words:
                if CNF._is_single_variable(word):
                    grandchildren.add(word)
            words.difference_update(grandchildren)
            words.update(self._recursive_descent(grandchildren))
        for child in children:
            words_to_return.update(self._rules[child])
        return words_to_return


    def _eliminate_remaining_unacceptable_rules(self):
        rules = self._rules
        # Base stores variables which have only one production rule that produces single terminal symbol.
        # Stores them just for grammar's compactness.
        base = {}
        for var, words in rules.items():
            if len(words) == 1:
                (word,) = words
                if word.islower():
                    base[word] = var

        new_rules = {}  # rules of new variables
        for var, words in rules.items():
            for word in words.copy():
                word_list = word.split('+')
                # Remaining unacceptable rules: A->[xX][yY][zZ]... (where the length of right-side is more than 2)
                # and A->aB, A->Ba, A->ab (right-side length is 2, but there is at least one terminal.
                # Solve these problems with additional variables and rules.
                if len(word_list) > 2 or len(word_list) == 2 and not (word_list[0] + word_list[1]).isupper():
                    words.remove(word)
                    lvar = var
                    for i in range(len(word_list) - 2):
                        if word_list[i].islower():
                            var1 = self._add_single_terminal_rule(word_list[i], base, new_rules)
                        else:
                            var1 = word_list[i]
                        var2 = self._generate_variable()
                        if i == 0:  # lvar == var => words == rules[lvar] == rules[var]
                            words.add(var1 + '+' + var2)
                        else:
                            new_rules[lvar] = {var1 + '+' + var2}
                        lvar = var2
                    i = len(word_list) - 2
                    if word_list[i].islower():
                        var1 = self._add_single_terminal_rule(word_list[i], base, new_rules)
                    else:
                        var1 = word_list[i]
                    if word_list[i + 1].islower():
                        var2 = self._add_single_terminal_rule(word_list[i + 1], base, new_rules)
                    else:
                        var2 = word_list[i + 1]
                    if i == 0:  # lvar == var => words == rules[lvar] == rules[var]
                        words.add(var1 + '+' + var2)
                    else:
                        new_rules[lvar] = {var1 + '+' + var2}
        rules.update(new_rules)

    def _add_single_terminal_rule(self, terminal, base, new_rules):
        if terminal in base:
            return base[terminal]
        else:
            var = self._generate_variable()
            base[terminal] = var
            new_rules[var] = {terminal}
            return var

    def __str__(self):
        # Some kind of readable format of grammar.
        l = []
        if self._empty_word:
            l.append("empty word\n")
        l.append("start: " + self._start + "\nterminals:")
        for terminal in sorted(self._terminals):
            l.append(" " + terminal)
        l.append("\nvariables:")
        for var in sorted(self._variables):
            l.append(" " + var)
        for var, words in sorted(self._rules.items()):
            l.append("\n" + var + " -> ")
            words_arr = sorted(words)
            l.append(words_arr[0])
            for i in range(1, len(words_arr)):
                l.append(" | " + words_arr[i])
        return ''.join(l)

    def parse(self, w):
        if not set(w).issubset(self._terminals):
            return False
        if len(w) == 0:
            if self._empty_word:
                return True
            else:
                return False

        # CYK algorithm here.
        n = len(w)
        variables = sorted(self._variables)
        d = {}
        rules = self._rules

        for var in variables:
            d[var] = [[False] * n for _ in range(n)]
            for i in range(n):
                if w[i] in rules[var]:
                    d[var][i][i] = True
        for diff in range(1, n):
            for i in range(n - diff):
                j = i + diff
                for var in variables:
                    result = False
                    for right in rules[var]:
                        if right[0].isupper():
                            v1, v2 = right.split('+')
                            for k in range(i, j):
                                result = result or d[v1][i][k] and d[v2][k + 1][j]
                    d[var][i][j] = result
        return d[self._start][0][n - 1]