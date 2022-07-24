import time
from collections import defaultdict
from typing import List, Tuple, Set, Dict, Optional, Union

from bubble import Bubble
from group import group
from oracle import ParseException
from parse_tree import ParseNode, ParseTreeList, build_grammar, START
from grammar import *
from token_expansion import expand_tokens
from union import UnionFind
from replacement_utils import get_strings_with_replacement, get_strings_with_replacement_in_rule, \
    lvl_n_derivable

from next_tid import allocate_tid

"""
Bulk of the Arvada algorithm.
"""

###################### Settings for ASE'21 Submission #########################
# MAX_SAMPLES_PER_COALESCE = 50   << number of strings to sample from the     #
#                                   grammar induced by a marge. Increase to   #
#                                   increase chance of catching unsound       #
#                                   merges, at the cost of runtime.           #
# MAX_GROUP_LEN = 10              << max number of elements in a bubble.      #
#                                   Reducing will decrease runtime of algo,   #
#                                   at cost of missing some bubblings         #
#                                                                             #
# MUST_EXPAND_IN_COALESCE = False << additional setting, requiring a merge to #
#                                   not only be valid, but also expand the    #
#                                   language accepted by the learned grammar  #
# MUST_EXPAND_IN_PARTIAL= False   << same thing but for partial merges        #
###############################################################################

MAX_SAMPLES_PER_COALESCE = 50
MIN_GROUP_LEN = 3
MAX_GROUP_LEN = 10

MUST_EXPAND_IN_COALESCE = False
MUST_EXPAND_IN_PARTIAL= False

ORIGINAL_COALESCE_TIME = 0
BUILD_TIME = 0
LAST_COALESCE_TIME = 0
EXPAND_TIME = 0
MINIMIZE_TIME = 0

TIME_GENERATING_EXAMPLES = 0
TIME_GROUPING = 0


def get_times():
    from replacement_utils import TIME_GENERATING_EXAMPLES_INTERNAL
    return {'FIRST_COALESCE' : ORIGINAL_COALESCE_TIME, 'BUILD': BUILD_TIME,
            'LAST_COALESCE' : LAST_COALESCE_TIME, 'EXPAND': EXPAND_TIME, 'MINIMIZE': MINIMIZE_TIME,
            'OVERALL_EXAMPLE_GEN': TIME_GENERATING_EXAMPLES + TIME_GENERATING_EXAMPLES_INTERNAL,
            'OVERALL_GROUPING': TIME_GROUPING}

def check_recall(oracle, grammar: Grammar):
    """
    Helper function to check whether grammar is consistent with oracle.
    """
    positives = grammar.sample_positives(10, 10)
    for pos in positives:
        try:
            oracle.parse(pos)
        except:
            return False
    return True

def build_start_grammar(oracle, leaves, bbl_bounds = (3,10)):
    """
    ORACLE is a CachingOracle or ExternalOracle with a .parse method, which
    returns True if the example given is in the ORACLE's language

    LEAVES is a list of positive examples, each  a list of characters.

    Returns a grammar that maximally expands LEAVES w.r.t. ORACLE.
    """
    global LAST_COALESCE_TIME
    global EXPAND_TIME
    global MINIMIZE_TIME
    global MIN_GROUP_LEN 
    global MAX_GROUP_LEN
    MIN_GROUP_LEN, MAX_GROUP_LEN = bbl_bounds
    print('Building the starting trees...'.ljust(50), end='\r')
    trees, classes = build_trees(oracle, leaves)
    print('Building initial grammar...'.ljust(50), end='\r')
    grammar = build_grammar(trees)
    print('Coalescing nonterminals...'.ljust(50), end='\r')
    s = time.time()
    grammar, new_trees, coalesce_caused = coalesce(oracle, trees, grammar)
    # grammar, new_trees, partial_coalesces = coalesce_partial(oracle, new_trees, grammar)
    LAST_COALESCE_TIME += time.time() - s
    s = time.time()
    grammar = expand_tokens(oracle, grammar, new_trees)
    EXPAND_TIME += time.time() - s
    print('Minimizing initial grammar...'.ljust(50), end='\r')
    s = time.time()
    grammar = minimize(grammar)
    MINIMIZE_TIME += time.time() - s
    return grammar


def build_naive_parse_trees(leaves: List[List[ParseNode]]):
    """
    Builds naive parse trees for each leaf in `leaves`, assigning each unique
    character to its own nonterminal, and uniting them all under the START
    nonterminal.
    """
    terminals = list(set([leaf.payload for leaf_lst in leaves for leaf in leaf_lst]))
    get_class = {t: allocate_tid() for t in terminals}

    def braces_tree(leaves: List[ParseNode], index: int, root: bool = False):
        """ 
        returns a initial parse tree based on brackets.
        input: a { b c}
        parse tree: 
             START
            / | | \
           a  { t1 }
                /\
                b c
        """
        
        children = []
        if root == False:
            
            children.append(ParseNode(get_class[leaves[index].payload], False, [leaves[index]]))
            index+=1
        while index<len(leaves):
            node = leaves[index]
            token = node.payload
            if token == "{" or token == "[" or token == "(":

                child, index = braces_tree(leaves, index)
                children.append(child)
            elif token == "}" or token == "]" or token == ")":
                children.append(ParseNode(get_class[token], False, [node]))
                return ParseNode(allocate_tid(), False, children), index
            else:
                children.append(ParseNode(get_class[token], False, [node]))
            index+=1

        return ParseNode(START, False, children)

    
    # trees = [ParseNode(START, False, [ParseNode(get_class[leaf.payload], False, [leaf]) for leaf in leaf_lst])
    #          for leaf_lst in leaves]
    trees=[]
    for leaf_list in leaves:
        new_children = braces_tree(leaf_list, 0, True)
        new_children.update_cache_info()
        # new_tree = ParseNode(START, False, new_children)
        trees.append(new_children)


    # for i in trees[0].children:
    #     print(i.payload, len(i.children))
    return trees


def build_naive_parse_trees_2(leaves: List[List[ParseNode]]):
    """
    Builds naive parse trees for each leaf in `leaves`, assigning each unique
    character to its own nonterminal, and uniting them all under the START
    nonterminal.
    """
    class_map = defaultdict(allocate_tid)
    trees = []
    for leaf_lst in leaves:
        children = []
        for leaf in leaf_lst:
            payload = leaf.payload
            if len(payload) == 1:
                children.append(ParseNode(class_map[payload], False, [leaf]))
            else:
                grandchildren = [ParseNode(class_map[c], False, [ParseNode(c, True, [])])for c in payload]
                children.append(ParseNode(class_map[payload], False, grandchildren))
        trees.append(ParseNode(START, False, children))
    # trees = [ParseNode(START, False, [ParseNode(get_class[leaf.payload], False, [leaf]) for leaf in leaf_lst])
    #          for leaf_lst in leaves]
    return trees


def apply(grouping: Bubble, trees: List[ParseNode]):
    """
    `grouping` is a Bubble, i.e. a representation of a  contiguous
    sequence of nonterminals that appears someplace in `trees`.

    `trees` is a list of parse trees

    Returns a new list of trees consisting of  bubbling up the grouping
    in `grouping` for each tree in `trees`
    """

    def matches(group_lst, layer):
        """
        GROUP_LST is a contiguous subarray of ParseNodes that are grouped together.
        This method requires that len(GRP_LST) > 0.

        LAYER another a list of ParseNodes.

        Returns the index at which GROUP_LST appears in LAYER, and returns -1 if
        the GROUP_LST does not appear in the LAYER. Does not mutate LAYER.
        """
        ng, nl = len(group_lst), len(layer)
        for i in range(nl):
            layer_ind = i  # Index into layer
            group_ind = 0  # Index into group
            while group_ind < ng and layer_ind < nl and layer[layer_ind].payload == group_lst[group_ind].payload:
                layer_ind += 1
                group_ind += 1
            if group_ind == ng: return i
        return -1

    def apply_single(tree: ParseNode):
        """
        TREE is a parse tree.

        Applies the GROUPING data structure to a single tree. Applies that
        GROUPING to LAYER as many times as possible. Does not mutate TREE.

        Returns the new layer. If no updates can be made, do nothing.
        """
        group_lst, id = grouping.bubbled_elems, grouping.new_nt
        new_tree, ng = tree.copy(), len(group_lst)

        # Do replacments in all the children first
        for index in range(len(new_tree.children)):
            # (self, payload, is_terminal, children)
            old_node = new_tree.children[index]
            new_tree.children[index] = apply_single(old_node)

        ind = matches(group_lst, new_tree.children)
        while ind != -1:
            parent = ParseNode(id, False, new_tree.children[ind: ind + ng])
            new_tree.children[ind: ind + ng] = [parent]
            ind = matches(group_lst, new_tree.children)

        new_tree.update_cache_info()
        return new_tree

    return [apply_single(tree) for tree in trees]


def build_trees(oracle, leaves):
    """
    ORACLE is an oracle for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    LEAVES should be a list of lists (one list for each input example), where
    each sublist contains the tokens that built that example, as ParseNodes.

    Iteratively builds parse trees by greedily choosing a substring to "bubble"
    up that passes replacement tests at each point in the algorithm, until no
    further bubble ups can be made.

    Returns a list of finished parse trees (as ParseNode) one for each list of
    leaf nodes in `leaves`.

    Algorithm:
        1. Over all top-level substrings:
            a. bubble up the substring
            b. perform replacement if possible
        2. If a replacement was possible, repeat (1)
    """
    global ORIGINAL_COALESCE_TIME
    global BUILD_TIME
    global TIME_GROUPING

    def score(trees: List[ParseNode], new_bubble: Optional[Bubble]) \
            -> Tuple[int, List[ParseNode]]:
        """
        Tries to merge nonterminals in `trees`, and returns (1, the new trees with labels)
        merged if a merge occurs. Score is 0 otherwise.

        If `new_bubble` is not None, only checks mergings that involve
        the new bubble (against each existing nonterminal if it's a 1-bubble
        and between the two introduced nonterminals if it's a 2-bubble)

        """
        # Convert LAYERS into a grammar
        grammar = build_grammar(trees)

        grammar, new_trees, coalesce_caused = coalesce(oracle, trees, grammar, new_bubble)
        # if not coalesce_caused and not isinstance(new_bubble, tuple):
        #     grammar, new_trees, partial_coalesces = coalesce_partial(oracle, trees, grammar, new_bubble)
        #     if partial_coalesces:
        #         print("\n(partial)")
        #         coalesce_caused = True

        # grammar = minimize(grammar)
        new_size = grammar.size()
        if coalesce_caused:
            return 1, new_trees
        else:
            return 0, trees


    best_trees = build_naive_parse_trees(leaves)
    grammar = build_grammar(best_trees)
    s = time.time()
    print("Beginning coalescing...".ljust(50))
    grammar, best_trees, _ = coalesce(oracle, best_trees, grammar)
    # grammar, best_trees, _ = coalesce_partial(oracle, best_trees, grammar)
    ORIGINAL_COALESCE_TIME += time.time() - s


    max_example_size = max([len(leaf_lst) for leaf_lst in leaves])
    print(f"max example size {max_example_size}")
    s = time.time()
    # Main algorithm loop. Iteratively increase the length of groups allowed from MIN_GROUP_LEN to MAX_GROUP_LEN
    # break the group_size loop if no valid merge after increasing group size by threshold
    threshold = 6
    for group_size in range(MIN_GROUP_LEN, MAX_GROUP_LEN):
        count = 1
        updated = True
        while updated:
            group_start = time.time()
            all_groupings = group(best_trees, group_size)
            TIME_GROUPING += time.time() - group_start
            updated, nlg = False, len(all_groupings)
            for i, (grouping, the_score) in enumerate(all_groupings):
                print(('[Group len %d] Bubbling iteration %d (%d/%d)...' % (group_size, count, i + 1, nlg)).ljust(50))
                ### Perform the bubble
                if isinstance(grouping, Bubble):
                    new_trees = apply(grouping, best_trees)
                    new_score, new_trees = score(new_trees, grouping)
                    grouping_str = f"Successful grouping (single): {grouping.bubbled_elems}\n    (aka {[e.derived_string() for e in grouping.bubbled_elems]}"
                    grouping_str += f"\n     [score of {the_score}]"
                else:
                    bubble_one = grouping[0]
                    bubble_two = grouping[1]
                    new_trees = apply(bubble_one, best_trees)
                    new_trees = apply(bubble_two, new_trees)
                    new_score, new_trees = score(new_trees, grouping)
                    grouping_str = f"Successful grouping (double): {bubble_one.bubbled_elems}, {bubble_two.bubbled_elems}"
                    grouping_str += f"\n     (aka {[e.derived_string() for e in bubble_one.bubbled_elems]}, {[e.derived_string() for e in bubble_two.bubbled_elems]}))"
                    grouping_str += f"\n     [score of {the_score}]"
                ### Score
                if new_score > 0:
                    print()
                    print(grouping_str)
                    best_trees = new_trees
                    updated = True
                    threshold = 6
                    break
            count = count + 1
        print("DECREMENT")
        threshold -= 1

        if group_size > max_example_size or threshold == 0:
            print(f"BREAK, group size {group_size}, threshold {threshold}")
            break

    BUILD_TIME += time.time() - s
    return best_trees, {}


def coalesce_partial(oracle, trees: List[ParseNode], grammar: Grammar,
                     coalesce_target: Bubble = None):
    """
    ASSUMES: `grammar` is the grammar induced by `trees`

    Performs partial coalesces on the grammar. That is, for pairs of nonterminals (nt1, nt2), checks whether:
       if nt1 can be replaced by nt2 everywhere, are there any occurrences of nt2 where nt1 can replace nt2.
    An "occurrence" of nt2 is a location in a rule in grammar. So even if there are two separate trees
    where nt2 occurs in the subtree:
        nt0
       /  \
     nt3  nt2

     nt2 beside nt3 as a child of nt0 is considered only "one occurrence"

    For efficiency:
     While nt1 can range over all nonterminals in the grammar, nt2 ranges only over "character" nonterminals,
     that is those whose rules only expand to a single character. Character classes are allowc

    ASSUMES: coalesce(oracle, trees, grammar, coalesce_target) has been called previously. In this case, we will never
    be in the situation where (nt1, nt2) can partially coalesce and (nt2, nt1) can partially coalesce.

    """

    def partially_coalescable(replaceable_everywhere: str, replaceable_in_some_rules: str, trees: ParseTreeList) -> Dict[
        Tuple[str, Tuple[str]], List[int]]:
        """
        `replaceable_everywhere` and `replaceable_in_some_rules` are both nonterminals

        If `replaceable_in_some_rules` can replace `replaceable_everywhere` at every
        occurrence of `replaceable_everywhere`, returns the rules (expansions) in which
        `replaceable_in_some_rules` can be replaced by `replaceable_everywhere`
        """

        global TIME_GENERATING_EXAMPLES
        language_expanded = not MUST_EXPAND_IN_PARTIAL
        # Get all the expansions where `replaceable_in_some_rules` appears
        partial_replacement_locs: List[Tuple[Tuple[str, List[str]], int]] = []
        for rule_start, rule in grammar.rules.items():
            for body in rule.bodies:
                replacement_indices = [idx for idx, val in enumerate(body) if val == replaceable_in_some_rules]
                for idx in replacement_indices:
                    partial_replacement_locs.append(((rule_start, body), idx))

        s = time.time()
        # Get the set of strings derivable from `replaceable_everywhere`
        everywhere_derivable_strings = lvl_n_derivable(trees, replaceable_everywhere, 0 )

        # Get the set of strings derivable from `replaceable_in_some_rules`
        in_some_derivable_strings = lvl_n_derivable(trees, replaceable_in_some_rules, 0)

        TIME_GENERATING_EXAMPLES += time.time() - s

        # Check whether `replaceable_everywhere` is replaceable by `replaceable_in_some_rules` everywhere.
        everywhere_by_some_candidates = []
        for tree in trees:
            everywhere_by_some_candidates.extend(
                get_strings_with_replacement(tree, replaceable_everywhere, in_some_derivable_strings))


        if len(everywhere_by_some_candidates) > MAX_SAMPLES_PER_COALESCE:
            everywhere_by_some_candidates = random.sample(everywhere_by_some_candidates, MAX_SAMPLES_PER_COALESCE)
        else:
            random.shuffle(everywhere_by_some_candidates)

        if MUST_EXPAND_IN_PARTIAL and coalesce_target is not None and trees.represented_by_derived_grammar(everywhere_by_some_candidates):
            language_expanded = False
        else:
            language_expanded = MUST_EXPAND_IN_PARTIAL
            try:
                for replaced_str in everywhere_by_some_candidates:
                    oracle.parse(replaced_str)
            except Exception as e:
                return []

        if (len(everywhere_derivable_strings) == 0): return {}

        # Now check whether there are any rules where `replaeable_in_some_rules` is replaceable by
        # `replaceable_everywhere`
        replacing_positions: Dict[Tuple[str, Tuple[str]], List[int]] = defaultdict(list)
        for replacement_loc in partial_replacement_locs:
            rule, posn = replacement_loc
            candidate_strs = []
            for tree in trees:
                candidate_strs.extend(
                    get_strings_with_replacement_in_rule(tree, rule, posn, everywhere_derivable_strings))
            if len(candidate_strs) > MAX_SAMPLES_PER_COALESCE:
                candidate_strs = random.sample(candidate_strs, MAX_SAMPLES_PER_COALESCE)
            else:
                random.shuffle(candidate_strs)

            if MUST_EXPAND_IN_PARTIAL and coalesce_target is not None and trees.represented_by_derived_grammar(candidate_strs):
                replacing_positions[(rule[0], tuple(rule[1]))].append(posn)
                continue

            try:
                candidate_index = 0
                for candidate in candidate_strs:
                    candidate_index += 1
                    oracle.parse(candidate)
                replacing_positions[(rule[0], tuple(rule[1]))].append(posn)
                language_expanded = True
            except ParseException as e:
                continue

        if MUST_EXPAND_IN_PARTIAL and coalesce_target is not None and not language_expanded:
            return []
        return replacing_positions

    def get_updated_grammar(old_grammar, partial_replacement_locs: Dict[Tuple[str, Tuple[str]], List[int]],
                            full_replacement_nt: str, nt_to_partially_replace: str, new_nt: str):
        """
        Creates a copy of `old_grammar` so that the locations in `partial_replacement_locs` are replaced by `new_nt`, and all
        occurrences of `full_relacement_nt` are replaced by `new_nt`
        """
        # Keep track of whether nt to partially replace still occurs on some rhss
        partially_replace_on_rhs = False
        grammar = old_grammar.copy()
        alt_rule = Rule(new_nt)
        for (rule_start, body), posns in partial_replacement_locs.items():
            rule_to_update = grammar.rules[rule_start]
            body_posn = rule_to_update.bodies.index(list(body))
            for posn in posns:
                rule_to_update.bodies[body_posn][posn] = new_nt
        for rule in grammar.rules.values():
            for body in rule.bodies:
                for idx in range(len(body)):
                    if body[idx] == full_replacement_nt:
                        body[idx] = new_nt
                    elif body[idx] == nt_to_partially_replace:
                        partially_replace_on_rhs = True
        # Now fixup rules to remove any duplicate productions that may have been added during replacement.
        for rule in grammar.rules.values():
            unique_bodies = []
            for body in rule.bodies:
                if body not in unique_bodies:
                    unique_bodies.append(body)
            rule.bodies = unique_bodies
        alt_rule_bodies = grammar.rules[full_replacement_nt].bodies
        alt_rule_bodies.extend(grammar.rules[nt_to_partially_replace].bodies)
        grammar.rules.pop(full_replacement_nt)
        alt_rule.bodies = alt_rule_bodies
        grammar.add_rule(alt_rule)
        if not partially_replace_on_rhs:
            grammar.rules.pop(nt_to_partially_replace)
        return grammar

    def update_tree(new_tree: ParseNode, partial_replacement_locs: Dict[Tuple[str, Tuple[str]], List[int]],
                    full_replacement_nt: str, new_nt: str):
        """
        Updates `new_tree` s.t. the locations in `partial_replacement_locs` are replaced by `new_nt`, and all
        occurrences of `full_relacement_nt` are replaced by `new_nt`.
        """
        if new_tree.is_terminal:
            return new_tree
        my_body = tuple([child.payload for child in new_tree.children])
        for c in new_tree.children:
            update_tree(c, partial_replacement_locs, full_replacement_nt, new_nt)
        if (new_tree.payload, my_body) in partial_replacement_locs:
            posns = partial_replacement_locs[(new_tree.payload, my_body)]
            for posn in posns:
                prev_child = new_tree.children[posn]
                prev_child.payload = new_nt
        if new_tree.payload == full_replacement_nt:
            new_tree.payload = new_nt

    def get_updated_trees(trees: ParseTreeList, rules_to_replace: Dict[Tuple[str, Tuple[str]], List[int]],
                          replacer_orig: str, replacer: str):
        rest = []
        for tree in trees:
            new_tree = tree.copy()
            update_tree(new_tree, rules_to_replace, replacer_orig, replacer)
            rest.append(new_tree)
        return rest

    #################### END HELPERS ########################

    nonterminals = set(grammar.rules.keys())
    nonterminals.remove("start")
    nonterminals = list(nonterminals)

    # Ranging over the nonterminals that need to be fully replaced by the
    # other in the list (other must replace this one at every location)
    if coalesce_target is not None:
        fully_replaceable = [coalesce_target.new_nt]
    else:
        fully_replaceable = nonterminals

    # List of nonterminals that can be partially replaced (find the positions
    # at which other replaces this one)
    partially_replaceable = [nonterm for nonterm in nonterminals
                             if len(grammar.rules[nonterm].bodies) == 1 and len(grammar.rules[nonterm].bodies[0]) == 1
                             and grammar.rules[nonterm].bodies[0][0] not in nonterminals]

    # The main work of the function.
    replacement_happened = False
    fully_replaced = {}
    trees = ParseTreeList(trees, grammar)
    for nt_to_fully_replace in fully_replaceable:
        for nt_to_partially_replace in partially_replaceable:

            # Fixups because we created the lists fully_replaceable and partially_replaceable
            # before performing replacements. So we may have some out-dated labels.
            while nt_to_fully_replace in fully_replaced and nt_to_fully_replace != START:
                nt_to_fully_replace = fully_replaced[nt_to_fully_replace]
            while nt_to_partially_replace in fully_replaced and nt_to_partially_replace != START:
                nt_to_partially_replace = fully_replaced[nt_to_partially_replace]
            if nt_to_fully_replace == nt_to_partially_replace:
                continue

            # Delegate to helper to find of if (a) nt_to_fully_replace can be replaced by nt_to_partially_replace
            # everywhere, and if so (b) return the positions at which nt_to_partially_replace can be replaced
            # by nt_to_fully_replace
            replacement_positions = partially_coalescable(nt_to_fully_replace, nt_to_partially_replace, trees)

            if len(replacement_positions) > 0:
                #print(f"we found that {nt_to_partially_replace} could replace {nt_to_fully_replace} everywhere, "
                 #     f"and {nt_to_fully_replace} could replace {nt_to_partially_replace} at : {replacement_positions}")

                if nt_to_fully_replace == START:
                    new_nt = START
                else:
                    new_nt = allocate_tid()

                grammar = get_updated_grammar(grammar, replacement_positions, nt_to_fully_replace,
                                              nt_to_partially_replace, new_nt)
                inner_trees = get_updated_trees(trees, replacement_positions, nt_to_fully_replace, new_nt)
                trees = ParseTreeList(inner_trees, grammar)
                fully_replaced[nt_to_fully_replace] = new_nt
                replacement_happened = True

    trees = trees.inner_list
    return grammar, trees, replacement_happened


def coalesce(oracle, trees: List[ParseNode], grammar: Grammar,
             coalesce_target: Bubble = None):
    """
    ORACLE is a Oracle for the grammar we seek to find. We ask the oracle
    yes or no replacement questions in this method.

    TREES is a list of fully constructed parse trees.

    GRAMMAR is a GrammarNode that is the disjunction of the TREES.

    COALESCE_TARGET is the nonterminal we should be checking coalescing against,
    else due a quadratic check of all nonterminals against each other.

    This method coalesces nonterminals that are equivalent to each other.
    Equivalence is determined by replacement.

    RETURNS: the grammar after coalescing, the parse trees after coalescing,
    and whether any nonterminals were actually coalesced with each other
    (found equivalent).
    """

    def replacement_valid(replacer_derivable_strings, replacee, trees : ParseTreeList) -> Tuple[bool, Set[str]]:
        """
        Returns true if every string derivable from `replacee` in `trees` can be replaced
        by every string in `replacer_derivable_strings`
        """

        # Get the set of positive examples with strings derivable from replacer
        # replaced with strings derivable from replacee
        replaced_strings = set()
        for tree in trees:
            replaced_strings.update(get_strings_with_replacement(tree, replacee, replacer_derivable_strings))

        if len(replaced_strings) == 0:
            # TODO: See the failing doctest in bubble.py. Pickle below for a "real" example
            #import pickle
            #pickle.dump(coalesce_target, open('overlap-bug.pkl', "wb"))
            #print(f"Oopsie with {coalesce_target}.\nPretty sure this is an overlap bug that I know of.... so let's just skip it")
            return False, set()
        #assert (replaced_strings)

        replaced_strings = list(replaced_strings)
        if len(replaced_strings) > MAX_SAMPLES_PER_COALESCE:
            replaced_strings = random.sample(replaced_strings, MAX_SAMPLES_PER_COALESCE)
        else:
            random.shuffle(replaced_strings)

        # Return True if all the replaced_strings are valid
        for s in replaced_strings:
            try:
                oracle.parse(s)
            except:
                return False, set()
        return True, set(replaced_strings)

    def replacement_valid_and_expanding(nt1, nt2, trees: ParseTreeList):
        """
        Returns true if nt1 and nt2 can be merged in the grammar while expanding the set of inputs accepted
        by the grammar, and not admitting any invalid inputs.
        """

        global TIME_GENERATING_EXAMPLES
        nt1_derivable_strings = set()
        nt2_derivable_strings = set()

        s = time.time()
        if isinstance(coalesce_target, tuple):
            nt1_derivable_strings.update(lvl_n_derivable(trees, nt1, 1))
            nt2_derivable_strings.update(lvl_n_derivable(trees, nt2, 1))
        else:
            nt1_derivable_strings.update(lvl_n_derivable(trees, nt1, 0))
            nt2_derivable_strings.update(lvl_n_derivable(trees, nt2, 0))
        TIME_GENERATING_EXAMPLES += time.time() - s

        # First check if the replacement is expanding
        if MUST_EXPAND_IN_COALESCE and coalesce_target is not None and nt1_derivable_strings == nt2_derivable_strings:
            return False

        nt1_valid, nt1_check_strings = replacement_valid(nt1_derivable_strings, nt2, trees)
        if not nt1_valid:
            return False
        nt2_valid, nt2_check_strings = replacement_valid(nt2_derivable_strings, nt1, trees)
        if not nt2_valid:
            return False


        if MUST_EXPAND_IN_COALESCE and coalesce_target is not None:
            if trees.represented_by_derived_grammar(nt1_check_strings) and \
                trees.represented_by_derived_grammar(nt2_check_strings):
                return False

        return True


    def get_updated_trees(get_class: Dict[str, str], trees):

        def replace_coalesced_nonterminals(node: ParseNode):
            """
                Rewrites node so that coalesced nonterminals point to their
                class nonterminal. For non-coalesced nonterminals, get_class
                just gives the original nonterminal
                """
            if node.is_terminal:
                return
            else:
                node.payload = get_class.get(node.payload, node.payload)
                for child in node.children:
                    replace_coalesced_nonterminals(child)

        def fix_double_indirection(node: ParseNode):
            """
                Fix parse trees that have an expansion of the for tx->tx (only one child)
                since we've removed such double indirection while merging nonterminals
                """
            if node.is_terminal:
                return

            while len(node.children) == 1 and node.children[0].payload == node.payload:
                # Won't go on forever because eventually length of children will be not 1,
                # or the children's payload will not be the same as the top node (e.g. if
                # the child is a terminal)
                node.children = node.children[0].children

            for child in node.children:
                fix_double_indirection(child)

        new_trees = []
        for tree in trees:
            new_tree = tree.copy()
            replace_coalesced_nonterminals(new_tree)
            fix_double_indirection(new_tree)
            new_trees.append(new_tree)
        return new_trees

    def get_updated_grammar(classes: Dict[str, List[str]], get_class: Dict[str, str], grammar):
        # Traverse through the grammar, and update each nonterminal to point to
        # its class nonterminal
        new_grammar = grammar.copy()
        for nonterm in new_grammar.rules:
            if nonterm == "start":
                continue
            for body in new_grammar.rules[nonterm].bodies:
                for i in range(len(body)):
                    # The keys of the rules determine the set of nonterminals
                    if body[i] in get_class:
                        body[i] = get_class[body[i]]
        # Add the alternation rules for each class into the grammar
        for class_nt, nts in classes.items():
            rule = Rule(class_nt)
            for nt in nts:
                old_rule = new_grammar.rules.pop(nt)
                for body in old_rule.bodies:
                    # Remove infinite recursions
                    if body == [class_nt]:
                        continue
                    rule.add_body(body)
            new_grammar.add_rule(rule)
        return new_grammar

    # height of the tree for reverse order traversal
    def get_height(treeNode: ParseNode):
        if treeNode.is_terminal:
            return 1
        max_height = -1
        for i in treeNode.children:
            max_height = max(max_height,get_height(i))
        return max_height + 1

    
    # prune tree at each non-terminal by reverse order
    def prune_tree(trees: List[ParseNode]):

        old_tree = None
        # helper for prune_tree
        def drop_reversed(parseNode, level, treeIndex):
            if parseNode.is_terminal or parseNode.children[0].is_terminal:
                return
            if level == 1:
                pruned = parseNode.copy()
                parseNode.children= [ParseNode("", True, [])]
                new_str = old_tree.derived_string()
                try:
                    oracle.parse(new_str)
                    trees[treeIndex] = old_tree
                    if pruned not in trees:
                        trees.append(pruned)
                    print("valid:", old_tree.derived_string())
                except:
                    print("before", old_tree.derived_string())
                    parseNode.children = pruned.children
                    print("after", old_tree.derived_string())
                    pass

                return
                
            for i in parseNode.children:
                drop_reversed(i, level-1, treeIndex)

        lng = len(trees)
        for i in range(lng):
            height = get_height(trees[i])
            old_tree = trees[i].copy()
            
            for h in reversed(range(2, height-1)):
                drop_reversed(old_tree, h, i)
        for tree in trees:
            tree.update_cache_info()
                


    # Define helpful data structures
    nonterminals = set(grammar.rules.keys())
    nonterminals.remove("start")
    nonterminals = list(nonterminals)
    uf = UnionFind(nonterminals)

    # Get all unique pairs of nonterminals
    pairs = []
    if isinstance(coalesce_target, Bubble):
        first = coalesce_target.new_nt
        for second in nonterminals:
            if first == second:
                continue
            pairs.append((first, second))
    elif isinstance(coalesce_target, tuple):
        pair = (coalesce_target[0].new_nt, coalesce_target[1].new_nt)
        pairs.append(pair)
    else:
        for i in range(len(nonterminals)):
            for j in range(i + 1, len(nonterminals)):
                first, second = nonterminals[i], nonterminals[j]
                pairs.append((first, second))

    coalesce_caused = False
    coalesced_into = {}
    checked = set()
    tree_list = ParseTreeList(trees, grammar)
    for pair in pairs:
        first, second = pair
        # update the pair for the new grammar, because the pair was created before
        # we performed any merges. If one of the labels was merged, replace it with
        # its new label.
        while first in coalesced_into and first != START:
            first = coalesced_into[first]
        while second in coalesced_into and second != START:
            second = coalesced_into[second]
        # and check that it's still valid
        if first == second:
            continue
        if (first, second) in checked:
            continue
        else:
            checked.add((first, second))

        # If the nonterminals can replace each other in every context, they are replaceable
        if replacement_valid_and_expanding(first, second, tree_list):
            if first == START or second == START:
                class_nt = START
            else:
                class_nt = allocate_tid()
            classes = {class_nt: [first, second]}
            get_class = {first: class_nt, second: class_nt}
            coalesced_into[first] = class_nt
            coalesced_into[second] = class_nt
            grammar = get_updated_grammar(classes, get_class, grammar)
            new_inner_trees = get_updated_trees(get_class, tree_list.inner_list)
            tree_list = ParseTreeList(new_inner_trees, grammar)
            coalesce_caused = True

    trees = tree_list.inner_list
    # prune tree 
    if coalesce_caused:
        prune_tree(trees)
    # grammar = build_grammar(trees)
    return grammar, trees, coalesce_caused


def minimize(grammar):
    """
    Mutative method that deletes repeated rules from GRAMMAR and removes
    unnecessary layers of indirection..
    """

    def remove_repeated_rules(grammar: Grammar):
        """
        Mutative method that removes all repeated rule bodies in GRAMMAR.
        """
        for rule in grammar.rules.values():
            remove_idxs = []
            bodies_so_far = set()
            for i, body in enumerate(rule.bodies):
                body_str = ''.join(body)
                if body_str in bodies_so_far:
                    remove_idxs.append(i)
                else:
                    bodies_so_far.add(body_str)
            for idx in reversed(remove_idxs):
                rule.bodies.pop(idx)

    def update(grammar: Grammar, map):
        """
        Given a MAP with nonterminals as keys and list of strings as values,
        replaces every occurance of a nonterminal in MAP with its corresponding
        list of symbols in the GRAMMAR. Then, the rules defining
        the keys nonterminals in MAP in the grammar are removed.

        The START nonterminal must not appear in MAP, because its rule cannot
        be deleted.
        """
        assert (START not in map)
        for rule in grammar.rules.values():
            for body in rule.bodies:
                to_fix = [elem in map for elem in body]
                # Reverse to ensure that we don't mess up the indices
                while any(to_fix):
                    ind = to_fix.index(True)
                    nt = body[ind]
                    body[ind:ind + 1] = map[nt]
                    to_fix = [elem in map for elem in body]
        remove_lhs = [lhs for lhs in grammar.rules.keys() if lhs in map]
        for lhs in remove_lhs:
            grammar.rules.pop(lhs)
        grammar.cached_parser_valid = False
        grammar.cached_str_valid = False
        return grammar

    # Remove all the repeated rules from the grammar
    remove_repeated_rules(grammar)

    # Finds the set of nonterminals that expand directly to a single terminal
    # Let the keys of X be the set of these nonterminals, and the corresponding
    # values be the the SymbolNodes derivable from those nonterminals
    X, updated = {}, True  # updated determines the stopping condition

    while updated:
        updated = False
        for rule_start in grammar.rules:
            rule = grammar.rules[rule_start]
            bodies = rule.bodies
            if len(bodies) == 1 and len(bodies[0]) == 1 and (bodies[0][0] not in grammar.rules or bodies[0][0] in X):
                body = bodies[0]
                if rule.start not in X and rule.start != START:
                    X[rule.start] = [X[elem][0] if elem in X else elem for elem in body]
                    updated = True

    # Update the grammar so that keys in X are replaced by values
    grammar = update(grammar, X)

    # Finds the set of nonterminals that expand to a single string and that are
    # only used once in the grammar. Let the keys of Y be the set of these
    # nonterminals, and the corresponding values be the SymbolNodes derivable
    # from those nonterminals
    counts = defaultdict(int)
    for rule_node in grammar.rules.values():
        for rule_body in rule_node.bodies:
            for symbol in rule_body:
                if symbol in grammar.rules:
                    n = symbol
                    counts[n] += 1

    # Update the grammar so that keys in X are replaced by values
    used_once = [k for k in counts if counts[k] == 1 and k != START]
    Y = {k: grammar.rules[k].bodies[0] for k in used_once if len(grammar.rules[k].bodies) == 1}
    grammar = update(grammar, Y)

    remove_repeated_rules(grammar)

    return grammar
