/**
 * Alpine.js Component for the Schedule Calendar
 * 
 * @param {Array} initialEvents - A JSON array of events passed down from Django
 * @returns {Object} Alpine.js component data object
 */
function calendar(initialEvents = []) {
    return {
        // --- State Variables ---
        viewMode: 'month', // 'month' or 'week' view
        activeDate: new Date(), // The currently viewed date
        monthNames: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
        days: [], // Array holding the days to render in the grid
        events: initialEvents, // Events data from Django
        selectedEvent: null, // The event selected for viewing details
        isDetailsModalOpen: false, // Whether the details modal is open
        
        // --- Computed Properties ---
        get month() { return this.activeDate.getMonth(); },
        get year() { return this.activeDate.getFullYear(); },
        
        // --- Initialization ---
        init() {
            this.updateView();
        },
        
        // --- Modal Methods ---
        openEventDetails(event) {
            this.selectedEvent = event;
            this.isDetailsModalOpen = true;
        },
        
        // --- Utility Methods ---
        
        /**
         * Checks if a given date matches today's date
         */
        isToday(date, month, year) {
            const today = new Date();
            return date === today.getDate() && month === today.getMonth() && year === today.getFullYear();
        },
        
        /**
         * Triggers a recalculation of the calendar grid based on the current view mode
         */
        updateView() {
            if (this.viewMode === 'month') {
                this.getDays();
            } else {
                this.getWeekDays();
            }
        },
        
        /**
         * Calculates the days to display for a Month View
         */
        getDays() {
            let y = this.year;
            let m = this.month;
            let daysInMonth = new Date(y, m + 1, 0).getDate();
            let dayOfWeek = new Date(y, m, 1).getDay(); // 0-6 (Sun-Sat)
            
            let daysArray = [];
            
            // 1. Previous month's trailing days (Left completely blank intentionally)
            for (let i = 1; i <= dayOfWeek; i++) {
                daysArray.push({
                    date: '',
                    isCurrentMonth: false,
                    isToday: false,
                    fullDate: ''
                });
            }
            
            // 2. Current month's actual days
            for (let i = 1; i <= daysInMonth; i++) {
                daysArray.push({
                    date: i,
                    isCurrentMonth: true,
                    isToday: this.isToday(i, m, y),
                    fullDate: `${y}-${String(m + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`
                });
            }
            
            // 3. Next month's leading days (Left completely blank intentionally to fill 6 rows of 7 days)
            let totalCells = 42; 
            let currentCells = daysArray.length;
            for (let i = 1; i <= totalCells - currentCells; i++) {
                daysArray.push({
                    date: '',
                    isCurrentMonth: false,
                    isToday: false,
                    fullDate: ''
                });
            }
            
            this.days = daysArray;
        },
        
        /**
         * Calculates the days to display for a Week View
         */
        getWeekDays() {
            let curr = new Date(this.activeDate);
            let first = curr.getDate() - curr.getDay(); // First day is the day of the month - the day of the week
            
            let daysArray = [];
            for (let i = 0; i < 7; i++) {
                let next = new Date(curr.getFullYear(), curr.getMonth(), first + i);
                daysArray.push({
                    date: next.getDate(),
                    isCurrentMonth: next.getMonth() === this.month,
                    isToday: this.isToday(next.getDate(), next.getMonth(), next.getFullYear()),
                    fullDate: `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`
                });
            }
            this.days = daysArray;
        },
        
        // --- Navigation Controls ---
        
        /**
         * Move forward by one month or one week
         */
        next() {
            if (this.viewMode === 'month') {
                this.activeDate = new Date(this.year, this.month + 1, 1);
            } else {
                this.activeDate = new Date(this.year, this.month, this.activeDate.getDate() + 7);
            }
            this.updateView();
        },
        
        /**
         * Move backward by one month or one week
         */
        prev() {
            if (this.viewMode === 'month') {
                this.activeDate = new Date(this.year, this.month - 1, 1);
            } else {
                this.activeDate = new Date(this.year, this.month, this.activeDate.getDate() - 7);
            }
            this.updateView();
        },
        
        /**
         * Jump directly to today's date
         */
        goToToday() {
            this.activeDate = new Date();
            this.updateView();
        }
    }
}
