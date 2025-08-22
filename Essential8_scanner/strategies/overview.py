from abc import ABC, abstractmethod
import re

# base strategy code that every mitigation strategy will follow 
class Strategy(ABC):
    id = "GEN"           # short form for the strategy e.g. application code = AC, restrict admin privileges = RAP
    name = "Generic"     # visible strategy name in the menu i.e. what is visible to user 
    keywords = []        # detection criteria 
    regex_any = []       # regular expression patterns 
    exclude = []         # potential false positives

    def normalize(self, text: str) -> str:
        t = text.lower() # all text to be converted to lowercases 
        return t

    @abstractmethod
    def description(self) -> str:
        return "No description" # brief description of mitigation strategy - every child class msut provide their own description

    # detection logic 
    def match(self, raw_text: str):
        # normalise the OCR text
        t = self.normalize(raw_text)

        # check for any exclusions 
        for ex in self.exclude:
            if ex in t:
                return []

        hits = []

        # check for any keyword match 
        for kw in self.keywords:
            if kw in t:
                hits.append(kw)

        # check for any regex match 
        for pat in self.regex_any:
            if re.search(pat, t):
                hits.append(f"re:{pat}")

        # return the list of matched 
        return hits