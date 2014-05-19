article: references.bib article.tex
	pdflatex -shell-escape article.tex
	# bibtex references
	pdflatex -shell-escape article.tex
	pdflatex -shell-escape article.tex

partial:
	pdflatex -shell-escape article.tex

clean:
	rm -f *.log *.out *.aux *.bbl *.blg article.pdf
