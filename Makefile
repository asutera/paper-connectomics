all: article, response, diff

article: references.bib article.tex
	pdflatex -shell-escape  -halt-on-error article.tex
	bibtex article
	pdflatex -shell-escape  -halt-on-error article.tex
	pdflatex -shell-escape  -halt-on-error article.tex

response: references.bib response.tex
	pdflatex -shell-escape  -halt-on-error response.tex
	bibtex article
	pdflatex -shell-escape  -halt-on-error response.tex
	pdflatex -shell-escape  -halt-on-error response.tex

diff: references.bib diff.tex
	pdflatex -shell-escape  -halt-on-error diff.tex
	bibtex article
	pdflatex -shell-escape  -halt-on-error diff.tex
	pdflatex -shell-escape  -halt-on-error diff.tex

partial:
	pdflatex -shell-escape article.tex

clean:
	rm -f *.log *.out *.aux *.bbl *.blg article.pdf


zip: article
	zip -r article.zip *.tex *.cls *.bib images article.pdf Makefile
