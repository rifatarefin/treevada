import functools
import re
from typing import Tuple, List

from collections import defaultdict

from parse_tree import ParseNode
from replacement_utils import get_overlaps



@functools.lru_cache(maxsize=None)
def side_similarity(side, other_side, reversed = False):
    """
    Helper which computes the similarity of two lists, assumed to be the sides of contexts.

    - If the two lists are identical, returns 1/2
    - Else, adds 1/(2^(i+2)) to the match score for each ith element in the list that matches
        - Includes if both lists have empty ith element (i.e. are of len 2)
        - Excludes if both lists have "DUMMY" as an element at ith position

    Hardcoded with k = 4.

    TODO: no idea if the lru_cache() is actually helpful to the performance of this function.
    """
    if side == other_side:
        return 0.5
    score = 0
    for i in range(4):
        match_score = 1 / (2 ** (i + 2))
        pos = -(i+1) if reversed else i
        if i < len(side) and i < len(other_side):
            if side[pos] == 'DUMMY' or other_side[pos] == 'DUMMY':
                continue
            elif side[pos] == other_side[pos]:
                score += match_score
        elif len(side) == len(other_side):
            score += match_score
        else:
            break
    return score


class Context:
    """
    Encapsulates the k-context (hard-coded for k=4) of a bubble.
    """
    def __init__(self, lhs : Tuple[str], rhs: Tuple[str]):
        self.lhs = lhs[-4:]
        self.rhs = rhs[:4]

    def __eq__(self, other):
        if not isinstance(other, Context):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.lhs, self.rhs))

    def __str__(self):
        return f"{self.lhs}[...]{self.rhs}"

    def __repr__(self):
        return self.__str__()

    def similarity(self, other):
        """
        Compute the similarity of two contexts are the sum of their two side similarities.
        Ref. to function at top of file for `side_similarity`.
        """
        assert(isinstance(other, Context))
        if self == other:
            return 1
        else:
            lhs_score = side_similarity(self.lhs, other.lhs, reversed = True)
            rhs_score = side_similarity(self.rhs, other.rhs)
            return lhs_score + rhs_score


class Bubble:
    """
    Represents a `bubble`, that is, a sequence of terminals/nonterminals that are to be
    bubbled up into a new nonterminal. Provides utility methods to track occurrence of
    the sequence, the context in which it occurs, and its overlap with other sequences.
    """

    def __init__(self, new_nt: str, bubbled_elems: List[ParseNode], depth: int):
        self.new_nt = new_nt
        self.bubbled_elems = bubbled_elems
        self.bubble_str = ''.join([e.payload for e  in bubbled_elems])
        self.direct_parents = []
        self.occ_count = 1
        self.contexts = defaultdict(int)
        self.depth = depth
        # sources is a map of (tree idx, (child_idxs)) -> range which allows us to map back
        # to the range that was bubbled
        self.sources = defaultdict(list)

    def add_source(self, tree_idx: int, child_idxs: List[int], seq_range: Tuple[int,int]):
        self.sources[(tree_idx, tuple(child_idxs))].append(seq_range)

    def add_direct_parent(self, parent):
        self.direct_parents.append(parent)

    def add_occurrence(self):
        self.occ_count += 1

    def add_context(self, context_lhs: List[ParseNode], context_rhs: List[ParseNode]):
        context = Context(tuple([e.payload for e in context_lhs]), tuple([e.payload for e in context_rhs]))
        self.contexts[context] += 1

    def mark_successfully_bubbled(self):
        global SUCCESSFULLY_BUBBLED
        SUCCESSFULLY_BUBBLED.add(self.bubbled_str)

    def __str__(self):
        return f"Bubble({self.new_nt}->{self.bubbled_elems}, occs={self.occ_count}, contexts= {dict(self.contexts)}, sources={self.sources})"

    def __repr__(self):
        return self.__str__()
    # def get_new_nt(self):
    #     return self.new_nt
    #
    # def get_bubble_elems(self):
    #     return self.bubbled_elems

    def context_similarity(self, other):
        num_pairs = 0
        total_similarity = 0
        max_similarity = 0
        for context in self.contexts:
            for other_context in other.contexts:
                num_pairs += 1
                similarity = context.similarity(other_context)
                total_similarity += similarity
                max_similarity = max(max_similarity, similarity )
        max_match = max(len(self.contexts), len(other.contexts))
        return max_similarity#total_similarity/max_match#total_similarity/num_pairs

    def contains(self, other: "Bubble"):
        other_re = re.compile(f"{other.bubble_str}")
        return other.bubble_str in self.bubble_str

    def application_breaks_other(self, other):
        """
        The point of this function is to calculate whether `self` and `other` are overlapping,
        so whether we must apply these bubbles in a certain order.

        Returns a tuple of two boolean values:
        - If we apply self first, does that break the ability to bubble up other?
        - If we apply other first, does that break the ability to bubble up self?
        >>> c = ParseNode("c", False, [])
        >>> o = ParseNode("o", False, [])
        >>> r = ParseNode("r", False, [])
        >>> e = ParseNode("e", False, [])
        >>> t = ParseNode("t", False, [])
        >>> n = ParseNode("n", False, [])
        >>> bubble_0 = Bubble('t0', [c, o , r ])
        >>> bubble_1 = Bubble('t1', [c, o, r ,e])
        >>> bubble_0.add_source(0, [], (0, 2))
        >>> bubble_1.add_source(0, [], (0, 3))
        >>> bubble_1.application_breaks_other(bubble_0)
        (False, True)
        >>> bubble_0.application_breaks_other(bubble_1)
        (True, False)
        >>> bubble_2 = Bubble('t2', [r ,e, c, t])
        >>> bubble_2.add_source(0, [], (2,5))
        >>> bubble_1.application_breaks_other(bubble_2)
        (True, True)
        >>> bubble_2.add_source(1, [2], (0, 3))
        >>> bubble_2.application_breaks_other(bubble_1)
        (True, False)
        >>> bubble_1.application_breaks_other(bubble_2)
        (False, True)
        >>> bubble_1.add_source(2, [1], (2,5))
        >>> bubble_3 = Bubble('t3', [e, c, t])
        >>> bubble_3.add_source(0, [], (4, 6))
        >>> bubble_0.application_breaks_other(bubble_3)
        (False, False)
        >>> bubble_4 = Bubble('t4', [e, t, c])
        >>> bubble_4.add_source(0, [], (0,2))
        >>> bubble_5 = Bubble('t5', [c, t, c])
        >>> bubble_5.add_source(0, [], (2,4))
        >>> bubble_5.application_breaks_other(bubble_4)
        (True, True)
        >>> bubble_4.application_breaks_other(bubble_5)
        (True, True)
        """

        my_sources = self.sources
        their_sources = other.sources

        if not my_sources and not their_sources:
            print("ERROR: bubbles without sources")
            exit(1)

        self_breaks_other = True
        other_breaks_self = True

        for my_path in my_sources:
            if my_path in their_sources:
                my_ranges = my_sources[my_path]
                their_ranges = their_sources[my_path]
                for my_range in my_ranges:
                    for their_range in their_ranges:
                        if my_range[1] < their_range[0] or  my_range[0] > their_range[1]:
                            # in this case there's a location where they're not overlapping,
                            # so the other one will always exist
                           #  print(f"case1: {my_range}, {their_range}") covered
                            self_breaks_other = False
                            other_breaks_self = False
                        elif my_range[0] <= their_range[0] and their_range[1] <= my_range[1]:
                            # In this case, they are contained in us, so they break us but we don't break them
                            #print(f"case2: {my_range}, {their_range}") covered
                            self_breaks_other = False
                        elif their_range[0] <= my_range[0] and my_range[1] <= their_range[1]:
                            #print("case3: {my_range}, {their_range}") covered
                            other_breaks_self = False
            else:
                other_breaks_self = False

        if self_breaks_other:
            for their_path in their_sources:
                if their_path not in my_sources:
                    self_breaks_other = False

        return (self_breaks_other, other_breaks_self)


    def old_application_breaks_other(self, other):
        """
        The point of this function is to calculate whether `self` and `other` are overlapping,
        so whether we must apply these bubbles in a certain order. All this complication is
        to avoid having to explicitly track overlapping bubbles while constructing the subsequences,
        and in hindsight, that may have been a simpler and more robust thing to do.

        Returns a tuple of two boolean values:
        - If we apply self first, does that break the ability to bubble up other?
        - If we apply other first, does that break the ability to bubble up self?

        TODO: There is a known bug, which is exposed by one of the doctests.


        >>> c = ParseNode("c", False, [])
        >>> o = ParseNode("o", False, [])
        >>> r = ParseNode("r", False, [])
        >>> e = ParseNode("e", False, [])
        >>> t = ParseNode("t", False, [])
        >>> n = ParseNode("n", False, [])
        >>> start = ParseNode("START", False, [])
        >>> end = ParseNode("END", False, [])
        >>> bubble_0 = Bubble('t0', [c, o , r ])
        >>> bubble_1 = Bubble('t1', [c, o, r ,e])
        >>> bubble_1.old_application_breaks_other(bubble_0)
        (False, False)
        >>> bubble_0 = Bubble('t0', [t,t])
        >>> bubble_1.old_application_breaks_other(bubble_0)
        (False, False)
        >>> bubble_0 = Bubble('t0', [o, r, c])
        >>> bubble_1.old_application_breaks_other(bubble_0)
        (False, False)
        >>> bubble_1.add_context([start], [c, t, end]) # ^corect$
        >>> bubble_2 = Bubble('t2', [r ,e, c, t])
        >>> bubble_2.add_context([c, o], [end]) # ^corect$
        >>> bubble_1.old_application_breaks_other(bubble_2)
        (True, True)
        >>> bubble_2.old_application_breaks_other(bubble_1)
        (True, True)
        >>> bubble_1.add_context([e, n], [end]) # ^encore$, ^corect$
        >>> bubble_1.old_application_breaks_other(bubble_2)   #bubble_2 still only occurs in corect, so we'll have issues if we bubble it up
        (True, False)
        >>> bubble_2.old_application_breaks_other(bubble_1)  # but core occurs in encore, so ok
        (False, True)
        >>> bubble_2.add_context([start], [e, n, end]) # ^corect$, ^recten$
        >>> bubble_1.old_application_breaks_other(bubble_2)   # ok now; bubble_2 still happens in recten
        (False, False)
        >>> bubble_1 = Bubble('t1', [c, o, r ,e])
        >>> bubble_1.add_context([start], [c, t, end]) # ^corect$
        >>> bubble_1.old_application_breaks_other(bubble_2)   # core will bubble up in corect, rect in recten
        (False, True)
        >>> bubble_2.old_application_breaks_other(bubble_1)   # core only occurs in correct, so doesn't work the other way
        (True, False)
        >>> bubble_3 = Bubble('t1', [c, o])   #cottc
        >>> bubble_3.add_context([start], [t, t, c, end])
        >>> bubble_4 = Bubble('t2', [o, t, t, c])
        >>> bubble_4.add_context([start, c], [end])
        >>> bubble_4.old_application_breaks_other(bubble_3)
        (True, True)
        >>> bubble_3 = Bubble('t1', [c, o]) #ottco
        >>> bubble_3.add_context([start, o, t, t], [end])
        >>> bubble_4 = Bubble('t2', [o, t, t, c])
        >>> bubble_4.add_context([start], [o, end])
        >>> bubble_4.old_application_breaks_other(bubble_3)
        (True, True)
        >>> bubble_5 = Bubble('t1', [c,o]) #cottco
        >>> bubble_5.add_context([start], [t,t,c,o, end])
        >>> bubble_5.add_context([start,c,o,t,t], [end])
        >>> bubble_6 = Bubble('t2', [o,t,t,c])
        >>> bubble_6.add_context([start, c], [o, end])
        >>> bubble_6.old_application_breaks_other(bubble_5)
        (True, True)
        """

        self_lst = [e.payload for e in self.bubbled_elems]
        other_lst = [e.payload for e in other.bubbled_elems]
        if not set(self_lst).intersection(set(other_lst)):
            return False, False

        if self.contains(other):
            return False, False

        overlap_ranges = get_overlaps(self_lst, other_lst)
        if len(overlap_ranges) == 0:
            return False, False

        other_breaks_self = False
        self_breaks_other = False
        for overlap_range in overlap_ranges:
            if overlap_range[0][0] == 0:
                # in this case the overlap is like
                #    rect   [self]
                #  core       [other]
                # TODO: really should do this for all elements of the context... but who cares, let's just do it for 1

                directly_to_the_left_of_self_in_context = set([context.lhs[-1] for context in self.contexts])
                assert(overlap_range[0][1] > 0) # else it would be contained in self
                directly_to_the_left_of_other_in_match = {other_lst[overlap_range[0][1] - 1]}
                if directly_to_the_left_of_self_in_context == directly_to_the_left_of_other_in_match:
                    #   [o]rect   [self]
                    #  c o re       [other]
                    # directly_to_the_left_of_other == {o}
                    # directly_to_the_left_of_self = {o}
                    # if we apply other first,
                    # bubble will be    /    \
                    #                  (core)ct
                    # no other rects... so can't apply self
                    other_breaks_self = other_breaks_self or True
                else:
                    #   [o, START]rect   [self]
                    #  c o re       [other]
                    # directly_to_the_left_of_other == {o}
                    # directly_to_the_left_of_self = {o, START}
                    # if we apply other first,
                    # bubble will be    /    \
                    #                  (core)ct
                    # but recten still exists, so  can apply self
                    other_breaks_self = other_breaks_self or  False

                directly_to_the_right_of_other_in_context = set([context.rhs[0] for context in other.contexts])
                directly_to_the_right_of_self_in_match = {self_lst[overlap_range[-1][0] + 1]}
                if directly_to_the_right_of_self_in_match == directly_to_the_right_of_other_in_context:
                    #     re c t   [self]
                    #   core[c]       [other]
                    # directly_to_the_right_of_self == {c}
                    # directly_to_the_right_of_other = {c}
                    # if we apply self first,
                    # bubble will be    /\
                    #                  co (rect)
                    # no other cores... so can't apply other
                    self_breaks_other = self_breaks_other or True
                else:
                    #     re c t   [self]
                    #   core{c,END}       [other]
                    # directly_to_the_right_of_self == {c}
                    # directly_to_the_right_of_other = {c, END}
                    # if we apply self first,
                    # bubble will be    /\
                    #                  co (rect)
                    # but also encore still exits, so can still apply core
                    self_breaks_other = self_breaks_other or  False
            else:
                # in this case the overlap is like
                #  core       [self]
                #    rect   [other]
                directly_to_the_right_of_self_in_context = set([context.rhs[0] for context in self.contexts])
                assert (overlap_range[-1][1] < len(other_lst) - 1) # else it would be completely contained in
                directly_to_the_right_of_other_in_match = {other_lst[overlap_range[-1][1] + 1]}
                if directly_to_the_right_of_other_in_match == directly_to_the_right_of_self_in_context:
                    #  core[c]       [self]
                    #    re ct   [other]
                    # directly_to_the_right_of_self = {c} (contexts)
                    # directly_to_the_right_of_other = {c} (bubble)
                    # if we apply other first,
                    # bubble will be    /\
                    #                  co (rect)
                    # no other cores... so can't apply self
                    other_breaks_self = other_breaks_self or  True
                else:
                    #  core[c, END]       [self]
                    #    re ct   [other]
                    # directly_to_the_right_of_self = {c, END} (contexts)
                    # directly_to_the_right_of_other = {c} (bubble)
                    # if we apply other first,
                    # bubble will be    /\
                    #                  co (rect)
                    # but encore still exists, so ok
                    other_breaks_self = other_breaks_self or  False

                directly_to_the_left_of_other_in_context = set([context.lhs[-1] for context in other.contexts])
                directly_to_the_left_of_self_in_match = {self_lst[overlap_range[0][0] - 1]}

                if directly_to_the_left_of_self_in_match == directly_to_the_left_of_other_in_context:
                    #  core       [self]
                    #  [o]rect   [other]
                    # directly_to_the_left_of_self = {o} (bubble)
                    # directly_to_the_left_of_other = {o} (contextx)
                    # if we apply other first,
                    # bubble will be    /\
                    #                  co (rect)
                    # no other rects... so can't apply other
                    self_breaks_other = self_breaks_other or True
                else:
                    #  core       [self]
                    #  [o, START]rect   [other]
                    # directly_to_the_left_of_self = {o} (bubble)
                    # directly_to_the_left_of_other = {o, START} (contextx)
                    # if we apply other first,
                    # bubble will be    /\
                    #                  co (rect)
                    # but recten still exists, so ok
                    self_breaks_other = self_breaks_other or False

        return (self_breaks_other, other_breaks_self)