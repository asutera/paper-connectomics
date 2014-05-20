all: article

article: references.bib article.tex
	pdflatex -shell-escape  -halt-on-error article.tex
	# bibtex references
	pdflatex -shell-escape  -halt-on-error article.tex
	pdflatex -shell-escape  -halt-on-error article.tex

partial:
	pdflatex -shell-escape article.tex

clean:
	rm -f *.log *.out *.aux *.bbl *.blg article.pdf
