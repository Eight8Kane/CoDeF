MathJax = {
    tex: {inlineMath: [['$', '$'], ['\\(', '\\)']]},
};

function convertMathJax() {
    MathJax.texReset();
    MathJax.typesetClear();
    MathJax.typesetPromise();
}
