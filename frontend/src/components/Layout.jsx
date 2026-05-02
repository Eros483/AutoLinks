import Header from './Header'
import Editor from './Editor'
import Recommendations from './Recommendations'

function Layout() {
  return (
    <div className="al-app">
      <Header />
      <div className="al-layout">
        <Editor />
        <Recommendations />
      </div>
    </div>
  )
}

export default Layout