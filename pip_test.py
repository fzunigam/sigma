import re

out = "Successfully installed other-package-1.0 sigma-finance-0.2.0b1 yet-another-2.0"
match = re.search(r"sigma-finance-([\w\.-]+)", out)
if match:
    print(match.group(1))
