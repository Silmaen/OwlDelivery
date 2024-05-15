//
// function to toggle a box between open/close
//
function toggleContent(boxId) {
    const box = document.getElementById(boxId);
    let content = box.querySelector('.folding_box_content');
    const isContentExpanded = content.classList.contains('open');
    let header = box.querySelector('.folding_box_header');

    console.log("isContentExpanded:", isContentExpanded);
    if (isContentExpanded) {
        content.classList.remove('open');
        header.classList.remove('open');
    } else {
        content.classList.add('open');
        header.classList.add('open');
    }
}