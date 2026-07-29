const menuToggler = document.querySelector("#menu-toggler")
const body = document.querySelector("body")
const drawer = document.querySelector("#nav-drawer")
const overlay = document.querySelector(".overlay")
const content = document.querySelector(".content")

menuToggler?.addEventListener("click", (event) => {
	toggleSideDrawer()
})

overlay?.addEventListener("click", (event) => {
	toggleSideDrawer()
})

function toggleSideDrawer() {
	body?.classList.toggle("no-scroll")
	drawer?.classList.toggle("active")
	overlay?.classList.toggle("active")
	content?.classList.toggle("active")
}

const notificationBar = document.querySelector(".notification-bar")
if (notificationBar != null) {
	let notificationId = notificationBar.dataset.notificationId
	let ids = localStorage.getItem("notificationId")?.split(",")
	if (!ids?.includes(notificationId.toString())) {
		notificationBar.classList.add("active")
	}
}
function closeNotificationBar(notificationId) {
	notificationBar?.classList.remove("active")
	if (notificationBar != null) {
		let ids = localStorage.getItem("notificationId")
		ids += `,${notificationId}`
		localStorage.setItem('notificationId', ids);
	}
}

window.addEventListener("scroll", (event) => {
	if (window.pageYOffset > 200) {
		menuToggler.classList.remove("hide")
	} else {
		menuToggler.classList.add("hide")
	}
})

// Horizontal scroll
const horizontalScrollContainers = document.querySelectorAll(".d-horizontal-scroll")
horizontalScrollContainers?.forEach(container => {
	// Is contain scrollable?
	if (container.scrollWidth <= container.clientWidth) {
		container.classList.add("hide-controls")
		container.classList.add("center")
	}

	const previous = container.querySelector(".previous")
	const next = container.querySelector(".next")
	let width = container.querySelector("div").clientWidth
	width = width == 0 ? 200 : width

	previous.addEventListener("click", event => {
		container.scrollBy({
			left: -width,
			behavior: 'smooth'
		})
	})

	next.addEventListener("click", event => {
		container.scrollBy({
			left: width,
			behavior: 'smooth'
		})
	})
})