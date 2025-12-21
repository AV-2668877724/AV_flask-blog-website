function like(postId){
    const likeCount = document.getElementById(`likes-count-${postId}`);
    const likeButton = document.getElementById(`like-button-${postId}`);

    fetch(`/like-post/${postId}`, {
        method: 'POST',
    })
    .then((res) => res.json())
    .then((data) => {
        if (data.error) {
            alert(data.error);
            return;
        }
        likeCount.innerText = data.likes;
        if (data.liked) {
            likeButton.className = 'fas fa-thumbs-up text-primary';
        } else {
            likeButton.className = 'far fa-thumbs-up';
        }
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}